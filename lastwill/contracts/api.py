import datetime
import pika
import json
import requests
from os import path
import binascii
from ethereum import abi
from django.utils import timezone
from django.db.models import F
from django.http import Http404
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from .models import Contract, contract_details_types
from .serializers import ContractSerializer
from lastwill.main.views import index
from lastwill.settings import SOL_PATH, SIGNER, CONTRACTS_DIR, MESSAGE_QUEUE
from lastwill.permissions import IsOwner, IsStaff
from lastwill.parint import *
from lastwill.profile.models import Profile
from exchange_API import to_wish

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
#            return super().destroy(request, *args, **kwargs)
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
    
    assert(contract.user == request.user and request.user.email)
    assert(contract.state in ('CREATED', 'WAITING_FOR_PAYMENT'))

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

#    details = contract.get_details()
#    details.deploy()
    channel.basic_publish(
            exchange='',
            routing_key=MESSAGE_QUEUE,
            body=json.dumps({'status': 'COMMITTED', 'contractId': contract.id}),
            properties=pika.BasicProperties(type='launch'),
    )
    print('compilation request sended')
    connection.close()
    return Response('ok')
