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


class ContractViewSet(ModelViewSet):
    permission_classes = (IsStaff | IsOwner, )
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = (IsAuthenticated,)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.state in ('CREATED',):
            return super().destroy(request, *args, **kwargs)
        raise PermissionDenied()

    def get_queryset(self):
        result = self.queryset.order_by('-created_date')
        if self.request.user.is_staff:
            return result
        return result.filter(user=self.request.user)


@api_view()
def get_cost(request):
    heirs_num = int(request.query_params['heirs_num'])
    active_to = datetime.date(*map(int, request.query_params['active_to'].split('-')))
    check_interval = int(request.query_params['check_interval'])
    result = Contract.calc_cost(heirs_num, active_to, check_interval)
    return Response({'result': result})


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
