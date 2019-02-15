from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from lastwill.contracts.models import *
from lastwill.profile.models import *
from lastwill.settings import MY_WISH_URL
from lastwill.deploy.models import *
from lastwill.contracts.api_eos import *
from lastwill.consts import *


@api_view(http_method_names=['GET'])
def get_available_contracts(request):
    '''
    view for get available contracts
    :param request: (network_id)
    :return: list of available contracts
    '''
    token = request.META['HTTP_TOKEN']
    if not token:
        raise ValidationError({'result': 'Token not found'}, code=404)
    get_user_for_token(token)
    if 'network_id' not in request.data:
        return Response(AVAILABLE_CONTRACT_TYPES)
    else:
        if int(request.data['network_id']) not in (1, 2, 5, 6, 10, 11, 14, 15):
            raise ValidationError({'result': 'Wrong network id'}, code=404)
        return AVAILABLE_CONTRACT_TYPES[int(request.data['network_id'])]


