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
from lastwill.settings import SOL_PATH, SIGNER, CONTRACTS_DIR, MESSAGE_QUEUE
from lastwill.permissions import IsOwner, IsStaff
from lastwill.parint import *
from lastwill.profile.models import Profile
from exchange_API import to_wish
from lastwill.settings import SIGNER, DEPLOY_ADDR, TEST_ADDRESSES
from lastwill.contracts.models import contract_details_types, Contract


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
    result = Contract.get_details_model(contract_type).calc_cost(request.query_params)
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
             contract__contract_type=4,
             contract__user=request.user,
    )
    for ec in eth_contracts:
        details = ec.contract.get_details()
        if details.eth_contract_token == ec:
            if any([x.contract.state not in ('ENDED', 'CREATED') for x in ec.ico_details_token.all()]):
                state = 'running'
            elif any([not x.continue_minting and x.contract.state != 'CREATED' for x in ec.ico_details_token.all()]):
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
    return Response({int(x.id): {
            'address': x.address,
            'token_name': x.ico_details_token.all()[0].token_name,
            'token_short_name': x.ico_details_token.all()[0].token_short_name,
            'decimals': x.ico_details_token.all()[0].decimals,
    } for x in token_contracts})


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
    
    assert(contract.user == request.user)
    assert(contract.state in ('CREATED', 'WAITING_FOR_PAYMENT'))
    if contract.contract_type == 4 and contract.get_details().start_date < datetime.datetime.now().timestamp() + 5*60:
        return Response({'result': 1}, status=400)
    # TODO: if type==4 check token contract is not at active crowdsale
    cost = contract.cost
    wish_cost = to_wish('ETH', int(cost))
    if not Profile.objects.select_for_update().filter(
            user__email=request.user.email, balance__gte=wish_cost
    ).update(balance=F('balance') - wish_cost):
        raise Exception('no money')
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.save()

    connection = pika.BlockingConnection(pika.ConnectionParameters(
            'localhost',
            5672,
            'mywill',
            pika.PlainCredentials('java', 'java'),
    ))

    channel = connection.channel()
    channel.queue_declare(queue=MESSAGE_QUEUE, durable=True, auto_delete=False, exclusive=False)

    channel.basic_publish(
            exchange='',
            routing_key=MESSAGE_QUEUE,
            body=json.dumps({'status': 'COMMITTED', 'contractId': contract.id}),
            properties=pika.BasicProperties(type='launch'),
    )
    print('deploy request sended')
    connection.close()
    return Response('ok')


class ICOtokensView(View):

    def get(self, request, *args, **kwargs):

        address = request.GET.get('address', None)
        assert (EthContract.objects.filter(address=address) != [])
        sold_tokens = count_sold_tokens(address)
        return Response({'sold tokens': sold_tokens})


@api_view(http_method_names=['GET'])
@permission_classes((permissions.IsAdminUser,))
def get_statistics(request):

    # Statistic of currency

    mywish_info = json.loads(requests.get(
            'https://api.coinmarketcap.com/v1/ticker/mywish/?convert=ETH'
                                        ).content.decode())[0]

    btc_info = json.loads(requests.get(
            'https://api.coinmarketcap.com/v1/ticker/bitcoin/'
                                        ).content.decode())[0]

    eth_info = json.loads(requests.get(
            'https://api.coinmarketcap.com/v1/ticker/ethereum/'
                                        ).content.decode())[0]

    now = datetime.datetime.now()
    day = now - datetime.timedelta(days=1)

    # Statistic of users and contracts
    users = User.objects.all()
    new_users = users.filter(date_joined__lte=now, date_joined__gte=day)
    contracts = Contract.objects.all()
    contracts = contracts.exclude(address__in=TEST_ADDRESSES)
    new_contracts = contracts.filter(created_date__lte=now,
                                     created_date__gte=day)

    created = contracts.filter(state__in=['CREATED'])
    now_created = created.filter(created_date__lte=now, created_date__gte=day)
    active = contracts.filter(state__in=['ACTIVE', 'WAITING'])
    now_active = active.filter(created_date__lte=now, created_date__gte=day)
    done = contracts.filter(state__in=[
                                    'DONE', 'CANCELLED', 'ENDED', 'EXPIRED'])
    now_done = done.filter(created_date__lte=now, created_date__gte=day)
    error = contracts.filter(state__in=['WAITING_FOR_DEPLOYMENT', 'POSTPONED'])
    now_error = error.filter(created_date__lte=now, created_date__gte=day)

    answer = {'users': len(users),
                'contracts': len(contracts),
                'new_users': len(new_users),
                'new_contracts': len(new_contracts),
                'active_contracts': len(active),
                'created_contracts': len(created),
                'done': len(done),
                'error': len(error),
                'now_created': len(now_created),
                'now_active': len(now_active),
                'now_done': len(now_done),
                'now_error': len(now_error),
                'wish_price_usd': round(float(mywish_info['price_usd']), 2),
                'wish_usd_percent_change_24h': round(float(mywish_info[
                                 'percent_change_24h']), 2),
                'wish_price_eth': round(float(mywish_info['price_eth']), 5),
                'wish_eth_percent_change_24h': round(float(mywish_info[
                                 '24h_volume_eth']), 1),
                'btc_price_usd': round(float(btc_info['price_usd'])),
                'btc_percent_change_24h': round(float(btc_info[
                                 'percent_change_24h']), 1),
                'eth_price_usd': round(float(eth_info['price_usd'])),
                'eth_percent_change_24h': round(
                                 float(eth_info['percent_change_24h']), 1)
                             }

    for type in contract_details_types:
        print(type['model'])
        answer[type['name']] = type['model'].objects.filter().count()

    return JsonResponse(answer)
