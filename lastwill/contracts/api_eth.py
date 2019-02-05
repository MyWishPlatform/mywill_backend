from django.http import JsonResponse
from django.db.models import F
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from lastwill.contracts.api_eos import *
import lastwill.check as check
from lastwill.contracts.models import *
from lastwill.profile.models import *
from lastwill.settings import MY_WISH_URL
from lastwill.deploy.models import *
from lastwill.consts import *


@api_view(http_method_names=['POST'])
def create_eth_token(request):
    '''
    view for create eth token
    :param request: (admin_address, token_name, decimals,
    token_short_name, token_type, network_id)
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
        'token_type': request.data['token_type'],
        'token_holders': []
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
        'admin_address': contract_details.admin_address,
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
    view for show eth token
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
def edit_eth_token(request):
    '''
    view for edit params in  eth token
    :param request: contain contract id, editable field
    (admin_address, token_name, decimals, token_short_name, token_type)
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
def calculate_cost_eth_token_contract(request):
    eth_cost = int(CONTRACT_PRICE_ETH['TOKEN'] * NET_DECIMALS['ETH'])
    return Response({
        'ETH': str(int(eth_cost)),
        'WISH': str(int(eth_cost) * convert('ETH', 'WISH')['WISH']),
        'BTC': str(int(eth_cost) * convert('ETH', 'BTC')['BTC'])
    })


@api_view(http_method_names=['POST', 'DELETE'])
def delete_eth_token_contract(request):
    '''
    delete eth token
    :param request: contain contract_id
    :return: cost
    '''
    token = request.META['HTTP_TOKEN']
    if not token:
        raise ValidationError({'result': 'Token not found'}, code=404)
    user = get_user_for_token(token)
    contract = Contract.objects.get(id=int(request.data['contract_id']))
    if contract.user != user:
        raise ValidationError({'result': 'Wrong token'}, code=404)
    if contract.contract_type != 5:
        raise ValidationError({'result': 'Wrong contract id'}, code=404)
    contract.invisible = True
    contract.save()
    return Response('Contract with id {id} deleted'.format(id=contract.id))



@api_view(http_method_names=['POST'])
def deploy_eth_token(request):
    '''
    view for deploy eth token
    :param request: contain contract id
    :return:
    '''
    token = request.META['HTTP_TOKEN']
    if not token:
        raise ValidationError({'result': 'Token not found'}, code=404)
    user = get_user_for_token(token)
    contract = Contract.objects.get(id=int(request.data.get('contract_id')))
    if contract.user != user:
        raise ValidationError({'result': 'Wrong contract_id'}, code=404)
    if contract.state != 'CREATED':
        raise ValidationError({'result': 'Wrong state'}, code=404)
    contract_details = contract.get_details()
    contract_details.predeploy_validate()
    if contract.network.id == 1:
        eth_cost = int(CONTRACT_PRICE_ETH['TOKEN'] * NET_DECIMALS['ETH'])
        wish_cost = int(eth_cost) * convert('ETH', 'WISH')['WISH']
        if 'promo' in request.data:
            promo = request.data['promo'].upper()
            user_balance = UserSiteBalance.objects.get(user=user, subsite__site_name=MY_WISH_URL).balance
            wish_cost = check_promocode_in_api(promo, 15, user, user_balance, contract.id, wish_cost)
        if not UserSiteBalance.objects.select_for_update().filter(
                user=user, subsite__site_name=MY_WISH_URL, balance__gte=wish_cost
        ).update(balance=F('balance') - wish_cost):
            raise ValidationError({'result': 'You have not money'}, code=400)
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.save()
    queue = NETWORKS[contract.network.name]['queue']
    send_in_queue(contract.id, 'launch', queue)
    return Response({'id': contract.id, 'state': contract.state})
