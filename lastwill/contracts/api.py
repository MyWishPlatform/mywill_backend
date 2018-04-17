import datetime
import pika
import pytz
import json
import requests
from os import path
import binascii
from ethereum import abi
from django.utils import timezone
from django.db.models import F
from django.http import Http404
from django.http import JsonResponse
from django.views.generic import View
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Contract, contract_details_types, EthContract
from .serializers import ContractSerializer, count_sold_tokens
from lastwill.main.views import index
from lastwill.settings import SOL_PATH, SIGNER, CONTRACTS_DIR, BASE_DIR
from lastwill.permissions import IsOwner, IsStaff
from lastwill.parint import *
from lastwill.profile.models import Profile
from exchange_API import to_wish
from lastwill.promo.models import Promo, User2Promo
from lastwill.promo.api import check_and_get_discount
from lastwill.settings import SIGNER
from lastwill.contracts.models import contract_details_types, Contract
from lastwill.deploy.models import Network
from lastwill.payments.functions import create_payment


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
        if self.request.user.is_staff:
            return result
        return result.filter(user=self.request.user)


@api_view()
def get_cost(request):
    contract_type = int(request.query_params['contract_type'])
    network = Network.objects.get(id=request.query_params['network_id'])
    result = Contract.get_details_model(contract_type).calc_cost(request.query_params, network)
    return Response({'result': str(int(to_wish('ETH', result)))})


@api_view()
def get_code(request):
    with open(path.join(CONTRACTS_DIR, Contract.get_details_model(int(request.query_params['contract_type'])).sol_path)) as f:
        return Response({'result': f.read()})

@api_view()
def get_contract_types(request):
    return Response({x: contract_details_types[x]['name'] for x in range(len(contract_details_types))})

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


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(http_method_names=['POST'])
def pizza_delivered(request):

    order_id = request.data['order_id']
    contract = Contract.objects.get(contract_type=3, details_pizza__order_id=order_id)

    assert(contract.state == 'ACTIVE')

    code = request.data['code']

    if contract.get_details().code != code:
        return Response({'result': 'bad code'})
    print('pizza delivered')
    tr = abi.ContractTranslator(contract.abi)
    par_int = ParInt()
    nonce = int(par_int.parity_nextNonce(contract.owner_address), 16)
    print('nonce', nonce)

    Hp = 56478
    Cp = 56467

    response = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
            'source' : contract.owner_address,
            'data': binascii.hexlify(tr.encode_function_call('hotPizza', [int(contract.get_details().code), int(contract.get_details().salt)])).decode(),
            'nonce': nonce,
            'dest': contract.address,
            'gaslimit': max(Hp, Cp),
    }).content.decode())
    print('response', response)
    signed_data = response['result']
    print('signed_data', signed_data)
    par_int.eth_sendRawTransaction('0x'+signed_data)
    print('pizza ok!')

    return Response({'result': 'ok'})

@api_view(http_method_names=['POST'])
def deploy(request):
    contract = Contract.objects.get(id=request.data.get('id'))
    contract_details = contract.get_details()
    contract_details.predeploy_validate()

    assert(contract.user == request.user)
    assert(contract.state in ('CREATED', 'WAITING_FOR_PAYMENT'))
    # if contract.contract_type == 4 and contract.get_details().start_date < datetime.datetime.now().timestamp() + 5*60:
    #     return Response({'result': 1}, status=400)
    # if contract.contract_type == 5 and any([th.freeze_date is not None and th.freeze_date < datetime.datetime.now().timestamp() + 5*60 for th in contract.tokenholder_set.all()]):
    #     return Response({'result': 2}, status=400)
    # TODO: if type==4 check token contract is not at active crowdsale
    cost = contract.cost
    promo_str = request.data.get('promo', None)
    if promo_str:
        try:
            discount = check_and_get_discount(promo_str, contract.contract_type, request.user)
        except PermissionDenied:
           promo_str = None
        else:
           cost = cost - cost * discount / 100
    wish_cost = to_wish('ETH', int(cost))
    if not Profile.objects.select_for_update().filter(
            user=request.user, balance__gte=wish_cost
    ).update(balance=F('balance') - wish_cost):
        raise Exception('no money')
    create_payment(request.user.id, -wish_cost, '', 'ETH', cost, False)

    if promo_str:
        promo_object = Promo.objects.get(promo_str=promo_str.upper())
        User2Promo(user=request.user, promo=promo_object).save()
        Promo.objects.select_for_update().filter(
                promo_str=promo_str.upper()
        ).update(
                use_count=F('use_count') + 1,
                referral_bonus=F('referral_bonus') + wish_cost
        )
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.save()

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            'localhost',
            5672,
            'mywill',
            pika.PlainCredentials('java', 'java'),
    ))


    queue = NETWORKS[contract.network.name]['queue']
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True, auto_delete=False, exclusive=False)

    channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=json.dumps({'status': 'COMMITTED', 'contractId': contract.id}),
            properties=pika.BasicProperties(type='launch'),
    )
    print('deploy request sended')
    connection.close()
    return Response('ok')


@api_view(http_method_names=['POST'])
def i_am_alive(request):
    contract = Contract.objects.get(id=request.data.get('id'))
    assert(contract.user == request.user)
    assert(contract.state == 'ACTIVE')
    assert(contract.contract_type in (0, 1))

    connection = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost',
        5672,
        'mywill',
        pika.PlainCredentials('java', 'java'),
    ))

    queue = NETWORKS[contract.network.name]['queue']
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True, auto_delete=False,
                          exclusive=False)

    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps({'status': 'COMMITTED', 'contractId': contract.id}),
        properties=pika.BasicProperties(type='confirm_alive'),
    )
    connection.close()
    return Response('ok')


@api_view(http_method_names=['POST'])
def cancel(request):
    contract = Contract.objects.get(id=request.data.get('id'))
    assert(contract.user == request.user)
    assert(contract.contract_type in (0, 1))
    assert(contract.state in ['ACTIVE', 'EXPIRED'])

    connection = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost',
        5672,
        'mywill',
        pika.PlainCredentials('java', 'java'),
    ))

    queue = NETWORKS[contract.network.name]['queue']
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True, auto_delete=False,
                          exclusive=False)

    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps({'status': 'COMMITTED', 'contractId': contract.id}),
        properties=pika.BasicProperties(type='cancel'),
    )
    connection.close()
    return Response('ok')


class ICOtokensView(View):

    def get(self, request, *args, **kwargs):

        address = request.GET.get('address', None)
        assert (EthContract.objects.filter(address=address) != [])
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
    active = contracts.filter(state__in=['ACTIVE', 'WAITING', 'WAITING_ACTIVATION'])
    now_active = active.filter(created_date__lte=now, created_date__gte=day)
    done = contracts.filter(state__in=[
        'DONE', 'CANCELLED', 'ENDED', 'EXPIRED', 'UNDER_CROWDSALE', 'TRIGGERED']
    )
    now_done = done.filter(created_date__lte=now, created_date__gte=day)
    error = contracts.filter(state__in=['POSTPONED'])
    now_error = error.filter(created_date__lte=now, created_date__gte=day)
    in_progress = contracts.filter(state__in=['WAITING_FOR_DEPLOYMENT'])
    now_in_progress = in_progress.filter(created_date__lte=now, created_date__gte=day)
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
    for num, ctype in enumerate(contract_details_types):
        answer['contract_type_'+str(num)] = contracts.filter(contract_type=num).count()
        answer['contract_type_'+str(num)+'_new'] = contracts.filter(contract_type=num).filter(created_date__lte=now, created_date__gte=day).count()
    return answer


@api_view(http_method_names=['GET'])
# @permission_classes((permissions.IsAdminUser,))
def get_statistics(request):

    now = datetime.datetime.now()
    day = datetime.datetime.combine(datetime.datetime.now().today(), datetime.time(0, 0))

    users = User.objects.all().exclude(email='', password='', last_name='', first_name='').exclude(email__startswith='testermc')
    anonimys = User.objects.filter(email='', password='', last_name='', first_name='')
    new_users = users.filter(date_joined__lte=now, date_joined__gte=day)

    try:
        test_info = json.load(open(path.join(BASE_DIR, 'lastwill/contracts/test_addresses.json')))
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
    contracts = Contract.objects.all().exclude(user__in=anonimys).exclude(user__in=fb_test_users).exclude(user__email__in=test_addresses).exclude(user__email__startswith='testermc')
    for network in networks:
        answer[network.name] = get_contracts_for_network(network, contracts, now, day)

    return JsonResponse(answer)