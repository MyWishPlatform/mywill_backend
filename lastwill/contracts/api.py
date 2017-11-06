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
from lastwill.permissions import IsOwner, IsStaff
from lastwill.contracts.types import contract_types

class ContractViewSet(ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
#    permission_classes = (IsAuthenticated, IsStaff | IsOwner)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.state in ('CREATED', 'WAITING_FOR_PAYMENT'):
            return super().destroy(request, *args, **kwargs)
        raise PermissionDenied()

    def get_queryset(self):
        result = self.queryset.order_by('-created_date')
        if self.request.user.is_staff:
            return result
        return result.filter(user=self.request.user)


@api_view()
def get_cost(request):
    contract_type = int(request.query_params['contract_type'])
#    heirs_num = int(request.query_params['heirs_num'])
#    active_to = datetime.date(*map(int, request.query_params['active_to'].split('-')))
#    check_interval = int(request.query_params['check_interval'])
    result = Contract.get_details_model(contract_type).calc_cost(request.query_params)
    return Response({'result': result})


@api_view()
def get_code(request):
    with open(Contract.get_details_model(int(request.query_params['contract_type'])).sol_path) as f:
        return Response({'result': f.read()})

@api_view()
def get_contract_types(request):
    return Response({x: contract_types[x]['name'] for x in range(len(contract_types))})

@api_view()
def test_comp(request):
    contract = Contract.objects.get(id=request.query_params['id'])
    contract.compile()
    contract.save()
    return Response({'result': 'ok'})

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(http_method_names=['POST'])
def pizza_delivered(request):
    order_id = request.data['order_id']
    contract = Contract.objects.get(contract_type=3, details_pizza__order_id=order_id)
    code = request.data['code']
    if contract.get_details().code != code:
        return Response({'result': 'bad code'})
    return Response({'result': 'ok'})
