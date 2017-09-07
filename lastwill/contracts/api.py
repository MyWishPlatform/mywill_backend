import datetime
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from .models import Contract
from .serializers import ContractSerializer
from lastwill.main.views import index

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
    balance = request.data['balance']
    state = request.data['state']
    contract = Contract.objects.get(id=contract_id)
    if balance: # > contract.cost:
        contract.state = state
        contract.save()
#        if status == 'CONFIRMED': # deploy
# set next check
    return Response({'status': 'ok'})


@api_view()
def get_code(request):
    return Response({'result': ' { contract code } '})
