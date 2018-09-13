import datetime
import time
from os import path
from subprocess import Popen, PIPE

from django.utils import timezone
from django.db.models import F
from django.http import Http404
from django.http import JsonResponse
from django.views.generic import View
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework import viewsets
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from lastwill.settings import CONTRACTS_DIR, BASE_DIR, EOS_ATTEMPTS_COUNT
from lastwill.permissions import IsOwner, IsStaff
from lastwill.parint import *
from lastwill.profile.models import Profile
from lastwill.promo.models import Promo, User2Promo
from lastwill.promo.api import check_and_get_discount
from lastwill.contracts.models import Contract, WhitelistAddress, AirdropAddress, EthContract, send_in_queue, ContractDetailsInvestmentPool, InvestAddress
from lastwill.deploy.models import Network
from lastwill.payments.api import create_payment
import lastwill.check as check
from exchange_API import to_wish, convert
from .serializers import ContractSerializer, count_sold_tokens, WhitelistAddressSerializer, AirdropAddressSerializer


def check_and_apply_promocode(promo_str, user, cost, contract_type, cid):
    wish_cost = to_wish('ETH', int(cost))
    if promo_str:
        try:
            discount = check_and_get_discount(
                promo_str, contract_type, user
            )
        except PermissionDenied:
           promo_str = None
        else:
           cost = cost - cost * discount / 100
        promo_object = Promo.objects.get(promo_str=promo_str.upper())
        User2Promo(user=user, promo=promo_object, contract_id=cid).save()
        Promo.objects.select_for_update().filter(
                promo_str=promo_str.upper()
        ).update(
                use_count=F('use_count') + 1,
                referral_bonus=F('referral_bonus') + wish_cost
        )
    return cost


class ContractViewSet(ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = (IsAuthenticated, IsStaff | IsOwner)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.state in ('CREATED', 'WAITING_FOR_PAYMENT'):
            try:
                self.perform_destroy(instance)
            except Http404:
                pass
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise PermissionDenied()

    def get_queryset(self):
        result = self.queryset.order_by('-created_date')
        eos = self.request.query_params.get('eos', None)
        if eos is not None:
            eos = int(eos)
            if eos:
                result = result.filter(contract_type__in=(10, 11, 12))
            else:
                result = result.exclude(contract_type__in=(10, 12))
        if self.request.user.is_staff:
            return result
        return result.filter(user=self.request.user)


@api_view()
def get_code(request):
    with open(path.join(CONTRACTS_DIR, Contract.get_details_model(
            int(request.query_params['contract_type'])
    ).sol_path)) as f:
        return Response({'result': f.read()})


@api_view()
def test_comp(request):
    contract = Contract.objects.get(id=request.query_params['id'])
    contract.get_details().compile()
    contract.save()
    return Response({'result': 'ok'})

@api_view()
def get_token_contracts(request):
    if request.user.is_anonymous:
        return Response([])
    res = []
    eth_contracts = EthContract.objects.filter(
             contract__contract_type__in=(4,5),
             contract__user=request.user,
             address__isnull = False,
             contract__network = request.query_params['network'],
    )
    for ec in eth_contracts:
        details = ec.contract.get_details()
        if details.eth_contract_token == ec:
            if any([x.contract.contract_type == 4 and x.contract.state not in ('CREATED', 'ENDED') for x in ec.ico_details_token.all()]):
                state = 'running'
            elif any([x.contract.contract_type == 4 and not x.continue_minting and x.contract.state =='ENDED' for x in ec.ico_details_token.all()]):
                state = 'closed'
            elif any([x.contract.contract_type == 5 and x.contract.state == 'ENDED' for x in ec.token_details_token.all()]):
                state = 'closed'
            else:
                state = 'ok'
            res.append({
                    'id': ec.id,
                    'address': ec.address,
                    'token_name': details.token_name, 
                    'token_short_name': details.token_short_name,
                    'decimals': details.decimals,
                    'state': state
            })
    return Response(res)


@api_view(http_method_names=['POST'])
def deploy(request):
    eos = request.data.get('eos', False)
    contract = Contract.objects.get(id=request.data.get('id'))
    contract_details = contract.get_details()
    contract_details.predeploy_validate()

    if contract.user != request.user or contract.state not in ('CREATED', 'WAITING_FOR_PAYMENT'):
        raise PermissionDenied

    # TODO: if type==4 check token contract is not at active crowdsale
    if eos:
        cost = contract_details.calc_cost_eos(contract_details, contract.network)
        currency = 'EOS'
    else:
        cost = contract.cost
        currency = 'ETH'
    promo_str = request.data.get('promo', None)
    cost = check_and_apply_promocode(
        promo_str, request.user, cost, contract.contract_type, contract.id
    )
    create_payment(request.user.id, '', currency, -cost)
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.save()
    queue = NETWORKS[contract.network.name]['queue']
    send_in_queue(contract.id, 'launch', queue)
    return Response('ok')


@api_view(http_method_names=['POST'])
def i_am_alive(request):
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.user != request.user or contract.state != 'ACTIVE' or contract.contract_type not in (0, 1):
        raise PermissionDenied
    details = contract.get_details()
    if details.last_press_imalive:
        delta = timezone.now() - details.last_press_imalive
        if delta.days < 1:
            test_logger.error('i am alive error')
            raise PermissionDenied(3000)
    queue = NETWORKS[contract.network.name]['queue']
    send_in_queue(contract.id, 'confirm_alive', queue)
    details.last_press_imalive = timezone.now()
    details.save()
    return Response('ok')


@api_view(http_method_names=['POST'])
def cancel(request):
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.user != request.user or contract.state not in ('ACTIVE', 'EXPIRED') or contract.contract_type not in (0, 1):
        raise PermissionDenied()
    queue = NETWORKS[contract.network.name]['queue']
    send_in_queue(contract.id, 'cancel', queue)
    return Response('ok')


class ICOtokensView(View):

    def get(self, request, *args, **kwargs):

        address = request.GET.get('address', None)
        if not EthContract.objects.filter(address=address):
            raise PermissionDenied
        sold_tokens = count_sold_tokens(address)
        return Response({'sold tokens': sold_tokens})


def get_users(names):
    users = []
    for name in names:
        first_name, last_name = name.split()
        user = User.objects.filter(
            last_name=last_name,
            first_name=first_name
        ).first()
        if user:
            users.append(user)
    return users


def get_currency_statistics():
    mywish_info = json.loads(requests.get(
        'https://api.coinmarketcap.com/v1/ticker/mywish/'
    ).content.decode())[0]

    mywish_info_eth = json.loads(requests.get(
        'https://api.coinmarketcap.com/v1/ticker/mywish/?convert=ETH'
    ).content.decode())[0]

    btc_info = json.loads(requests.get(
        'https://api.coinmarketcap.com/v1/ticker/bitcoin/'
    ).content.decode())[0]

    eos_info = json.loads(requests.get(
        'https://api.coinmarketcap.com/v1/ticker/eos/'
    ).content.decode())[0]

    eth_info = json.loads(requests.get(
        'https://api.coinmarketcap.com/v1/ticker/ethereum/'
    ).content.decode())[0]
    answer = {
        'wish_price_usd': round(
        float(mywish_info['price_usd']), 10),
                          'wish_usd_percent_change_24h': round(
        float(mywish_info[
                  'percent_change_24h']), 10
        ),
    'wish_price_eth': round(float(mywish_info_eth['price_eth']), 10),
    'wish_eth_percent_change_24h': round(
        float(eth_info['percent_change_24h']) / float(
            mywish_info_eth['percent_change_24h']), 10
    ),
    'btc_price_usd': round(float(btc_info['price_usd'])),
    'btc_percent_change_24h': round(float(
        btc_info['percent_change_24h']), 10
    ),
    'eth_price_usd': round(
        float(eth_info['price_usd'])),
    'eth_percent_change_24h': round(
        float(eth_info['percent_change_24h']), 10
    ),
    'eos_price_usd':  round(
        float(eos_info['price_usd'])),
    'eos_percent_change_24h': round(
        float(eos_info['percent_change_24h']), 10
        ),
    'eos_rank': eos_info['rank'],
    'mywish_rank': mywish_info['rank'],
    'bitcoin_rank': btc_info['rank'],
    'eth_rank': eth_info['rank']
    }
    return answer


def get_contracts_for_network(net, all_contracts, now, day):
    contracts = all_contracts.filter(network=net)
    new_contracts = contracts.filter(created_date__lte=now,
                                     created_date__gte=day)
    created = contracts.filter(state__in=['CREATED'])
    now_created = created.filter(created_date__lte=now, created_date__gte=day)
    active = contracts.filter(
        state__in=['ACTIVE', 'WAITING', 'WAITING_ACTIVATION']
    )
    now_active = active.filter(created_date__lte=now, created_date__gte=day)
    done = contracts.filter(
        state__in=[
            'DONE', 'CANCELLED', 'ENDED', 'EXPIRED',
            'UNDER_CROWDSALE', 'TRIGGERED', 'KILLED'
        ]
    )
    now_done = done.filter(created_date__lte=now, created_date__gte=day)
    error = contracts.filter(state__in=['POSTPONED'])
    now_error = error.filter(created_date__lte=now, created_date__gte=day)
    in_progress = contracts.filter(state__in=['WAITING_FOR_DEPLOYMENT'])
    now_in_progress = in_progress.filter(
        created_date__lte=now, created_date__gte=day
    )
    answer = {
        'contracts': len(contracts),
        'new_contracts': len(new_contracts),
        'active_contracts': len(active),
        'created_contracts': len(created),
        'done': len(done),
        'error': len(error),
        'now_created': len(now_created),
        'now_active': len(now_active),
        'now_done': len(now_done),
        'now_error': len(now_error),
        'launch': len(in_progress),
        'now_launch': len(now_in_progress)
        }
    contract_details_types = Contract.get_all_details_model()
    for ctype in contract_details_types:
        answer['contract_type_'+str(ctype)] = contracts.filter(
            contract_type=ctype
        ).count()
        answer['contract_type_'+str(ctype)+'_new'] = contracts.filter(
            contract_type=ctype
        ).filter(created_date__lte=now, created_date__gte=day).count()
    return answer


@api_view(http_method_names=['GET'])
# @permission_classes((permissions.IsAdminUser,))
def get_statistics(request):

    now = datetime.datetime.now()
    day = datetime.datetime.combine(
        datetime.datetime.now().today(),
        datetime.time(0, 0)
    )

    users = User.objects.all().exclude(
        email='', password='', last_name='', first_name=''
    ).exclude(email__startswith='testermc')
    anonymous = User.objects.filter(
        email='', password='', last_name='', first_name=''
    )
    new_users = users.filter(date_joined__lte=now, date_joined__gte=day)

    try:
        test_info = json.load(open(
            path.join(BASE_DIR, 'lastwill/contracts/test_addresses.json')
        ))
        test_addresses = test_info['addresses']
        persons = test_info['persons']
        fb_test_users = get_users(persons)
    except(FileNotFoundError, IOError):
        test_addresses = []
        fb_test_users = []

    answer = {
        'user_statistics': {'users': len(users), 'new_users': len(new_users)},
        'currency_statistics': get_currency_statistics()
    }
    networks = Network.objects.all()
    contracts = Contract.objects.all().exclude(
        user__in=anonymous
    ).exclude(
        user__in=fb_test_users
    ).exclude(
        user__email__in=test_addresses
    ).exclude(
        user__email__startswith='testermc'
    )
    for network in networks:
        answer[network.name] = get_contracts_for_network(
            network, contracts, now, day
        )

    return JsonResponse(answer)

@api_view(http_method_names=['GET'])
def get_statistics_landing(request):
    now = datetime.datetime.now()
    day = datetime.datetime.combine(
        datetime.datetime.now().today(),
        datetime.time(0, 0)
    )
    users = User.objects.all().exclude(
        email='', password='', last_name='', first_name=''
    ).exclude(email__startswith='testermc')
    anonymous = User.objects.filter(
        email='', password='', last_name='', first_name=''
    )
    new_users = users.filter(date_joined__lte=now, date_joined__gte=day)

    try:
        test_info = json.load(open(
            path.join(BASE_DIR, 'lastwill/contracts/test_addresses.json')
        ))
        test_addresses = test_info['addresses']
        persons = test_info['persons']
        fb_test_users = get_users(persons)
    except(FileNotFoundError, IOError):
        test_addresses = []
        fb_test_users = []

    contracts = Contract.objects.all().exclude(user__in=anonymous).exclude(
        user__in=fb_test_users
    ).exclude(
        user__email__in=test_addresses
    ).exclude(
        user__email__startswith='testermc'
    )
    new_contracts = contracts.filter(
        created_date__lte=now, created_date__gte=day
    )
    answer = {
        'contracts': len(contracts),
        'new_contracts': len(new_contracts),
        'users': len(users),
        'new_users': len(new_users)
    }
    return JsonResponse(answer)


@api_view(http_method_names=['GET'])
def get_cost_all_contracts(request):
    eos = request.query_params.get('eos', False)
    answer = {}
    contract_details_types = Contract.get_all_details_model()
    for i in contract_details_types:
        if i > 9 and eos:
            answer[i] = contract_details_types[i]['model'].min_cost_eos() / 10**4
        else:
            answer[i] = contract_details_types[i]['model'].min_cost() / 10 ** 18
    return JsonResponse(answer)

@api_view(http_method_names=['POST'])
def neo_crowdsale_finalize(request):
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.user != request.user or contract.contract_type != 7 or contract.state != 'ACTIVE':
        raise PermissionDenied
    neo_details = contract.get_details()
    now = datetime.datetime.now().timestamp()
    if neo_details.stop_date <= now:
        contract.state = 'ENDED'
        contract.save()
        return JsonResponse({'result': 2})
    raise ValidationError({'result': 2}, code=403)


class ReadOnly(BasePermission):

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class WhitelistAddressViewSet(viewsets.ModelViewSet):
    queryset = WhitelistAddress.objects.all()
    serializer_class = WhitelistAddressSerializer
    permission_classes = (ReadOnly,)

    def get_queryset(self):
        result = self.queryset
        contract_id = self.request.query_params.get('contract', None)
        if not contract_id:
            raise ValidationError()
        contract = Contract.objects.get(id=contract_id)
        if contract.user != self.request.user:
            raise ValidationError({'result': 2}, code=403)
        result = result.filter(contract=contract, active=True)
        return result


class AirdropAddressViewSet(viewsets.ModelViewSet):
    queryset = AirdropAddress.objects.all()
    serializer_class = AirdropAddressSerializer
    permission_classes = (ReadOnly,)

    def get_queryset(self):
        result = self.queryset
        contract_id = self.request.query_params.get('contract', None)
        if not contract_id:
            raise ValidationError()
        contract = Contract.objects.get(id=contract_id)
        if contract.user != self.request.user:
            raise ValidationError({'result': 2}, code=403)
        result = result.filter(contract=contract, active=True)
        state = self.request.query_params.get('state', None)
        if state:
            result = result.filter(state=state)
        result = result.order_by('id')
        return result


@api_view(http_method_names=['POST'])
def load_airdrop(request):
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.user != request.user or contract.contract_type != 8 or contract.state != 'ACTIVE':
        raise PermissionDenied
    if contract.airdropaddress_set.filter(state__in=('processing', 'sent')).count():
        raise PermissionDenied
    print('air deleting', flush=True)
    contract.airdropaddress_set.all().delete()
    print('air inserting', flush=True)
    addresses = request.data.get('addresses')
    AirdropAddress.objects.bulk_create([AirdropAddress(
            contract=contract,
            address=x['address'].lower(),
            amount=x['amount']
    ) for x in addresses])
    print('air ok', flush=True)
    return JsonResponse({'result': 'ok'})


@api_view(http_method_names=['GET'])
def get_contract_for_link(request):
    details = ContractDetailsInvestmentPool.objects.get(
        link=request.query_params['link'],
        contract__state__in=('ACTIVE', 'CANCELLED', 'DONE', 'ENDED')
    )
    contract = details.contract
    return JsonResponse(ContractSerializer().to_representation(contract))

@api_view(http_method_names=['GET'])
def get_invest_balance_day(request):
    contract = Contract.objects.get(id=request.query_params['id'])
    now_date = datetime.datetime.now()
    if now_date.minute > 30:
        if now_date.hour != 23:
            date = datetime.datetime(
                now_date.year, now_date.month,
                now_date.day, now_date.hour + 1, 0, 0
            )
        else:
            date = datetime.datetime(
                now_date.year, now_date.month,
                now_date.day, 0, 0, 0
            )
    else:
        date = datetime.datetime(
            now_date.year, now_date.month,
            now_date.day, now_date.hour, 0, 0
        )
    # date = datetime.datetime.now().date()
    invests = InvestAddress.objects.filter(contract=contract, created_date__lte=date)
    balance = 0
    for inv in invests:
        balance = balance + inv.amount
    if balance == 0:
        balance = str(balance)
    return JsonResponse({'last_balance': balance})


@api_view(http_method_names=['POST'])
def check_status(request):
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.user != request.user or contract.state != 'ACTIVE':
        raise PermissionDenied
    if contract.contract_type != 12:
        raise PermissionDenied
    details = contract.get_details()
    now = datetime.datetime.now().timestamp()
    addr = details.crowdsale_address
    host = NETWORKS[contract.network.name]['host']
    port = NETWORKS[contract.network.name]['port']
    command = ['cleos', '-u', 'http://%s:%s' % (host,port), 'get', 'table', addr, addr, 'state']
    stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()
    if stdout:
        result = json.loads(stdout.decode())['rows'][0]
        if now > result['finish'] and int(result['total_tokens']) < details.soft_cap:
            contract.state = 'CANCELLED'
            contract.save()
        elif details.is_transferable_at_once and now > result['finish'] and int(result['total_tokens']) >= details.soft_cap:
            contract.state = 'DONE'
            contract.save()        
        elif details.is_transferable_at_once and int(result['total_tokens']) >= details.hard_cap:
            contract.state = 'DONE'
            contract.save()
    return JsonResponse(ContractSerializer().to_representation(contract))


@api_view(http_method_names=['POST', 'GET'])
def get_eos_cost(request):
    eos_url = 'http://%s:%s' % (
        str(NETWORKS['EOS_MAINNET']['host']),
        str(NETWORKS['EOS_MAINNET']['port'])
    )
    command1 = [
        'cleos', '-u', eos_url, 'get', 'table', 'eosio', 'eosio', 'rammarket'
    ]
    for attempt in range(EOS_ATTEMPTS_COUNT):
        print('attempt', attempt, flush=True)
        stdout, stderr = Popen(command1, stdin=PIPE, stdout=PIPE,
                               stderr=PIPE).communicate()
        print(stdout, stderr, flush=True)
        result = stdout.decode()
        if result:
            ram = json.loads(result)['rows'][0]
            print('result', result, flush=True)
            print('ram', ram, flush=True)
            print('quote', ram['quote']['balance'].split(), flush=True)
            print('base', ram['base']['balance'].split(), flush=True)
            ram_price = float(ram['quote']['balance'].split()[0]) / float(
                ram['base']['balance'].split()[0]) * 1024
            break
    else:
        print('stderr', stderr, flush=True)
        raise Exception(
            'cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)
    print('get ram price', flush=True)
    ram = request.query_params['buy_ram_kbytes']
    net = request.query_params['stake_net_value']
    cpu = request.query_params['stake_cpu_value']
    eos_cost = (float(ram) * ram_price + float(net) + float(cpu)) * 2
    print('eos cost', eos_cost, flush=True)
    return JsonResponse({'EOS': round(eos_cost, 0)})
