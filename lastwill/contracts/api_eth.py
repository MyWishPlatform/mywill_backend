import datetime

from django.http import JsonResponse
from django.db.models import F
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from lastwill.contracts.serializers import *
from lastwill.contracts.api_eos import *
import lastwill.check as check
from lastwill.contracts.models import *
from lastwill.other.models import *
from lastwill.profile.models import *
from lastwill.promo.models import *
from lastwill.settings import EOSISH_URL
from lastwill.deploy.models import *
from lastwill.consts import *


@api_view(http_method_names=['POST'])
def create_eth_token(request):
    '''
    view for create eos account
    :param request: contain account_name, owner_public_key, active_public_key, token, network_id
    :return: ok
    '''
    token = request.META['HTTP_TOKEN']
    if not token:
        raise ValidationError({'result': 'Token not found'}, code=404)
    user = get_user_for_token(token)
    if int(request.data['network_id']) not in [1, 2]:
        raise ValidationError({'result': 'Wrong network id'}, code=404)
    network = Network.objects.get(id=int(request.data['network_id']))
    check.is_address(request.data['admin_address'])
    if int(request.data['decimals']) < 0 or int(request.data['decimals']) > 50:
        raise ValidationError({'result': 'Wrong decimals'}, code=404)
    if request.data['token_type'] not in ['ERC20', 'ERC23']:
        raise ValidationError({'result': 'Wrong token type'}, code=404)
    token_params = {
        'decimals': int(request.data['decimals']),
        'token_name': request.data['token_name'],
        'token_short_name': request.data['token_short_name'],
        'admin_address': request.data['admin_address'],
        'token_type': request.data['token_type']
    }
    Contract.get_details_model(
        5
    ).calc_cost(token_params, network)
    contract = Contract(
        state='CREATED',
        name='Contract',
        contract_type=5,
        network=network,
        cost=0,
        user=user
    )
    contract.save()

    contract_details = ContractDetailsTokenSerializer().create(contract, token_params)
    answer = {
        'state': contract.state,
        'admin_address': contract_details.account_name,
        'token_short_name': contract_details.token_short_name,
        'token_name': contract_details.token_name,
        'id': contract.id,
        'created_date': contract.created_date,
        'network': contract.network.name,
        'network_id': contract.network.id,
        'decimals': contract_details.decimals,
        'token_type': contract_details.token_type
    }
    return Response(answer)


@api_view(http_method_names=['GET'])
def show_eth_token(request):
    '''
    view for show eos account
    :param request: contain contract id
    :return:
    '''
    # token = request.data['token']
    token = request.META['HTTP_TOKEN']
    if not token:
        raise ValidationError({'result': 'Token not found'}, code=404)
    user = get_user_for_token(token)
    contract = get_object_or_404(Contract, id=int(request.data['contract_id']))
    if contract.invisible:
        raise ValidationError({'result': 'Contract is deleted'}, code=404)
    if contract.user != user:
        raise ValidationError({'result': 'Wrong token'}, code=404)
    contract_details = contract.get_details()
    answer = {
        'state': contract.state,
        'id': contract.id,
        'created_date': contract.created_date,
        'network': contract.network.name,
        'network_id': contract.network.id,
        'token_name': contract_details.token_name,
        'token_short_name': contract_details.token_short_name,
        'admin_address': contract_details.admin_address,
        'decimals': contract_details.decimals,
        'token_type': contract_details.token_type
    }
    return JsonResponse(answer)


@api_view(http_method_names=['PUT', 'PATCH'])
def edit_eos_account(request):
    '''
    view for edit params in  eos account
    :param request: contain contract id, editable field
    (account_name, public_key, cpu, net, ram)
    :return:
    '''
    token = request.META['HTTP_TOKEN']
    if not token:
        raise ValidationError({'result': 'Token not found'}, code=404)
    user = get_user_for_token(token)
    contract = Contract.objects.get(id=int(request.data['contract_id']))
    if contract.state != 'CREATED':
        raise ValidationError({'result': 'Wrong status in contract'}, code=403)
    if contract.user != user:
        raise ValidationError({'result': 'Wrong token'}, code=404)
    contract_details = contract.get_details()
    if 'decimals' in request.data and int(request.data['decimals']) >= 0 and int(request.data['decimals']) <= 50:
        contract_details.decimals = int(request.data['decimals'])
    if 'token_type' in request.data and request.data['token_type'] in ['ERC20', 'ERC23']:
        contract_details.token_type = request.data['token_type']
    if 'token_short_name' in request.data and request.data['token_short_name'] != '':
        contract_details.token_short_name = request.data['token_short_name'].upper()
    if 'admin_address' in request.data:
        check.is_address(request.data['admin_address'])
        contract_details.admin_address = request.data['admin_address']
    if 'token_name' in request.data and request.data['token_name'] != '':
        contract_details.token_name = request.data['token_name']
    contract_details.save()
    answer = {
        'state': contract.state,
        'id': contract.id,
        'created_date': contract.created_date,
        'network': contract.network.name,
        'network_id': contract.network.id,
        'token_name': contract_details.token_name,
        'token_short_name': contract_details.token_short_name,
        'admin_address': contract_details.admin_address,
        'decimals': contract_details.decimals,
        'token_type': contract_details.token_type
    }
    return Response(answer)


@api_view(http_method_names=['GET'])
def calculate_cost_eos_account_contract(request):
    eth_cost = int(CONTRACT_PRICE_ETH['TOKEN'] * NET_DECIMALS['ETH'])
    return Response({
        'ETH': str(int(eth_cost)),
        'WISH': str(int(eth_cost) * convert('ETH', 'WISH')['WISH']),
        'BTC': str(int(eth_cost) * convert('ETH', 'BTC')['BTC'])
    })