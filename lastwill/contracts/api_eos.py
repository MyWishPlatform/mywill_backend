import datetime
from os import path
from subprocess import Popen, PIPE
import requests

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

from lastwill.settings import CONTRACTS_DIR, BASE_DIR
import lastwill.check as check
from lastwill.contracts.models import send_in_queue
from lastwill.contracts.serializers import *
from lastwill.contracts.models import *


# def validate_params(request):
#     data = request.data
#     if 'admin_address' not in data:
#         raise ValidationError({'result': 2}, code=403)
#     check.is_eos_address(data['admin_address'])
#     if 'token_account' not in data:
#         raise ValidationError({'result': 2}, code=403)
#     check.is_eos_address(data['token_account'])



@api_view()
def create_eos_token(request):
    '''
    view for create eos token
    :param request: contain token_short_name, token_account,
    decimals, maximum_supply
    :return: ok
    '''
    network = Network.objects.get(id=10)
    contract = Contract(
        state='CREATED',
        name='Contract',
        contract_type=14,
        network=network,
        cost=0,
        user_id=32
    )
    contract.save()
    eos_contract = EOSContract(
        address=None,
        source_code='',
        abi={},
        bytecode='',
        compiler_version=None,
        constructor_arguments=''
    )
    eos_contract.save()
    token_params = {}
    token_params['decimals'] = int(request.query_params['decimals'])
    token_params['maximum_supply'] = int(request.query_params['maximum_supply'])
    token_params['token_short_name'] = request.query_params['token_short_name']
    token_params['token_account'] = request.query_params['token_account']
    token_params['admin_address'] = request.query_params['admin_address']
    token_params['eos_contract'] = eos_contract
    ContractDetailsEOSTokenSASerializer().create(contract, token_params)
    return Response('ok')


@api_view()
def deploy_eos_token(request):
    '''
    view for deploy eos token
    :param request: contain contract id
    :return:
    '''
    contract = Contract.objects.get(id=request.query_params.get('id'))
    if contract.state != 'CREATED':
        raise ValidationError({'result': 2}, code=403)
    contract_details = contract.get_details()
    contract_details.predeploy_validate()
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.save()
    queue = NETWORKS[contract.network.name]['queue']
    send_in_queue(contract.id, 'launch', queue)
    return Response('ok')


@api_view()
def show_eos_token(request):
    '''
    view for show eos token
    :param request: contain contract id
    :return:
    '''
    contract = Contract.objects.get(id=request.query_params.get('id'))
    contract_details = contract.get_details()
    return ContractDetailsEOSTokenSASerializer().to_representation(contract_details)
