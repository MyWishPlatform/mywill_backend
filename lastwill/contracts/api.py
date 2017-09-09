import datetime
import json
import requests
import binascii
from ethereum import abi
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from .models import Contract
from .serializers import ContractSerializer
from lastwill.main.views import index
from lastwill.settings import SOL_PATH, SIGNER


class ContractViewSet(ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = (IsAuthenticated,)

    def destroy(self, *args, **kwargs):
        raise PermissionDenied()

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(user=self.request.user)


@api_view()
def get_cost(request):
    heirs_num = int(request.query_params['heirs_num'])
    active_to = datetime.date(*map(int, request.query_params['active_to'].split('-')))
    check_interval = int(request.query_params['check_interval'])
    result = Contract.calc_cost(heirs_num, active_to, check_interval)
    return Response({'result': result})


@api_view(['POST'])
def payment_notify(request):
    contract_id = request.data['contractId']
    state = request.data['state']
    contract = Contract.objects.get(id=contract_id)
    if state == 'CONFIRMED' and contract.state == 'CREATED':
        balance = request.data['balance']
        if balance >= contract.cost:
            contract.compile()
            contract.save()
            tr = abi.ContractTranslator(contract.abi)
            arguments = [
                    contract.user_address,
                    [h.address for h in contract.heir_set.all()],
                    [h.percentage for h in contract.heir_set.all()],
#                    ['0x7e169Ef0a7915F9E6904b13308F9C995D2c295D6'],
#                    [100],
                    contract.check_interval,
                    '0xf4c716ec3a201b960ca75a74452e663b00cf58b9',
            ]
            nonce = int(json.loads(requests.post('http://127.0.0.1:8545/', json={
                    "method":"parity_nextNonce",
                    "params": [contract.owner_address],
                    "id":1,
                    "jsonrpc":"2.0"
            }, headers={'Content-Type': 'application/json'}).content.decode())['result'], 16)
            signed_data = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
                    'source' : contract.owner_address,
                    'data': contract.bytecode + binascii.hexlify(tr.encode_constructor_arguments(arguments)).decode(),
                    'nonce': nonce
            }).content.decode())['result']


#            return Response({'signed_data': signed_data})

            result = json.loads(requests.post('http://127.0.0.1:8545/', json={
                    "method":"eth_sendRawTransaction",
                    "params": ['0x' + signed_data],
                    "id":1,
                    "jsonrpc":"2.0"
            }, headers={'Content-Type': 'application/json'}).content.decode())

            contract.address = '0x'+binascii.hexlify(utils.mk_contract_address(contract.owner_address, nonce)).decode()

#            return Response({'result': result})
            
    # set next check
    contract.state = state
    contract.save()            
    return Response({'status': 'ok'})


@api_view()
def get_code(request):
    with open(SOL_PATH) as f:
        return Response({'result': f.read()})

@api_view()
def test_comp(request):
    contract = Contract.objects.get(id=request.query_params['id'])
    contract.compile()
    contract.save()
    return Response({'result': 'ok'})
