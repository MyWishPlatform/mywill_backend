from http import HTTPStatus
from xmlrpc.client import ResponseError

import near_api
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

import lastwill.check as check
from lastwill.consts import *
from lastwill.contracts.api_eos import *
from lastwill.contracts.api_eth import *
from lastwill.contracts.models import *
from lastwill.contracts.submodels.near.token import init_account
from lastwill.deploy.models import *
from lastwill.profile.models import *
from lastwill.settings import MY_WISH_URL


def check_account_exists(admin_address: str):
    mywish_account = init_account()
    try:
        mywish_account._provider.get_account(admin_address)
    except near_api.providers.JsonProviderError:
        raise ValidationError('Admin address account does not exist')


@api_view(http_method_names=['POST'])
def create_near_contract(request):
    '''
    view for create near token
    :param request: (admin_address, token_name, decimals,
    token_short_name, maximum_supply, network_id)
    :return: ok
    '''
    if request.user.is_anonymous:
        return HttpResponse(status=403)
    user = request.user
    # потом добавить, если будем пилить мейннет
    if int(request.data['network_id']) not in [40]:
        raise ValidationError({'result': 'Wrong network id'}, code=404)
    network = Network.objects.get(id=int(request.data['network_id']))
    if int(request.data['network_id']) == 40:
        check.is_near_address_testnet(request.data['admin_address'])
        check_account_exists(request.data['admin_address'])
    else:
        check.is_near_address(request.data['admin_address'])
        check_account_exists(request.data['admin_address'])
    if int(request.data['decimals']) < 0 or int(request.data['decimals']) > 64:
        raise ValidationError({'result': 'Wrong decimals'}, code=404)
    if request.data['token_type'] not in ['NEP-141']:
        raise ValidationError({'result': 'Wrong token type'}, code=404)
    validate_token_name(request.data['token_name'])
    validate_token_short_name(request.data['token_short_name'])
    if request.data['future_minting'] not in [True, False]:
        raise ValidationError({'result': 'Wrong future minting'}, code=404)
    token_params = {
        'decimals': int(request.data['decimals']),
        'token_type': request.data['token_name'],
        'token_name': request.data['token_name'],
        'token_short_name': request.data['token_short_name'],
        'admin_address': request.data['admin_address'],
        'future_minting': request.data['future_minting'],
        'maximum_supply': request.data['maximum_supply'],
        'token_holders': []
    }
    Contract.get_details_model(40).calc_cost(token_params, network)
    # Add consts to price etc.
    contract = Contract(state='CREATED', name='Contract', contract_type=40, network=network, cost=0, user=user)
    contract.save()
    contract_details = ContractDetailsNearTokenSerializer().create(contract, token_params)
    answer = {
        'state': contract.state,
        'admin_address': contract_details.admin_address,
        'token_short_name': contract_details.token_short_name,
        'token_name': contract_details.token_name,
        'contract_id': contract.id,
        'created_date': contract.created_date,
        'network': contract.network.name,
        'network_id': contract.network.id,
        'decimals': contract_details.decimals,
        'future_minting': contract_details.future_minting,
    }
    return Response(answer)


@api_view(http_method_names=['POST'])
def deploy_near_contract(request):
    '''
    view for deploy near token
    :param request: contain contract id
    :return: id, state
    '''
    if request.user.is_anonymous:
        return HttpResponse(status=403)
    user = request.user
    contract = Contract.objects.get(id=int(request.data.get('contract_id')))
    if contract.user != user:
        raise ValidationError({'result': 'Wrong contract_id'}, code=404)
    if contract.invisible:
        raise ValidationError({'result': 'Contract is deleted'}, code=404)
    if contract.state not in ['CREATED', 'WAITING_FOR_DEPLOYMENT']:
        raise ValidationError({'result': 'Wrong status in contract'}, code=404)
    contract_details = contract.get_details()
    contract_details.predeploy_validate()
    # for MAINNET
    # if contract.network.id == 40:
    #     eth_cost = int(CONTRACT_PRICE_ETH['TOKEN'] * NET_DECIMALS['ETH'])
    #     wish_cost = int(eth_cost) * rate('ETH', 'WISH').value
    #     if 'promo' in request.data:
    #         promo = request.data['promo'].upper()
    #         user_balance = UserSiteBalance.objects.get(user=user, subsite__site_name=MY_WISH_URL).balance
    #         wish_cost = check_promocode_in_api(promo, 15, user, user_balance, contract.id, wish_cost)
    #     if not UserSiteBalance.objects.select_for_update().filter(
    #             user=user, subsite__site_name=MY_WISH_URL, balance__gte=wish_cost
    #     ).update(balance=F('balance') - wish_cost):
    #         raise ValidationError({'result': 'You have not money'}, code=400)
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.deploy_started_at = datetime.datetime.now()
    contract.save()
    
    answer = {
        'state': contract.state,
        'admin_address': contract_details.admin_address,
        'deploy_address': contract_details.deploy_address,
        'token_short_name': contract_details.token_short_name,
        'token_name': contract_details.token_name,
        'contract_id': contract.id,
        'created_date': contract.created_date,
        'network': contract.network.name,
        'network_id': contract.network.id,
        'token_type': contract_details.token_type,
        'decimals': contract_details.decimals,
        'future_minting': contract_details.future_minting,
        'total_supply': contract_details.maximum_supply,
        'tx_hash': contract_details.near_contract.tx_hash,
    }
    
    # деплоим напрямую, сканера нет
    try:
        contract_details.deploy()
    except Exception:
        traceback.print_exc()
        contract.state = 'POSTPONED'
        contract.save()
        return JsonResponse(answer)
    # проверяем успешность деплоя
    try:
        contract_details.initialized()
    except Exception:
        traceback.print_exc()
        contract.state = 'POSTPONED'
        contract.save()
        return JsonResponse(answer)
    return JsonResponse(answer)


@api_view(http_method_names=['GET'])
def show_near_contract(request):
    '''
    view for show near token
    :param request: contain contract id
    :return:
    '''
    if request.user.is_anonymous:
        return HttpResponse(status=403)
    user = request.user
    contract = get_object_or_404(Contract, id=int(request.data['contract_id']))
    if contract.invisible:
        raise ValidationError({'result': 'Contract is deleted'}, code=404)
    if contract.user != user:
        raise ValidationError({'result': 'Wrong token'}, code=404)
    contract_details = contract.get_details()
    answer = {
        'state': contract.state,
        'contract_id': contract.id,
        'created_date': contract.created_date,
        'network': contract.network.name,
        'network_id': contract.network.id,
        'token_name': contract_details.token_name,
        'token_short_name': contract_details.token_short_name,
        'admin_address': contract_details.admin_address,
        'deploy_address': contract_details.deploy_address,
        'decimals': contract_details.decimals,
        'maximum_supply': contract_details.maximum_supply,
        'token_type': contract_details.token_type,
        'future_minting': contract_details.future_minting
    }
    if contract_details.near_contract_token and contract_details.near_contract_token.tx_hash:
        answer['tx_hash'] = contract_details.near_contract_token.tx_hash
    if contract_details.near_contract_token and contract_details.near_contract_token.address:
        answer['contract_address'] = contract_details.near_contract_token.address
    return JsonResponse(answer)


@api_view(http_method_names=['POST', 'DELETE'])
def delete_near_contract(request):
    '''
    delete near token
    :param request: contain contract_id
    :return: id
    '''
    if request.user.is_anonymous:
        return HttpResponse(status=403)
    user = request.user
    contract = Contract.objects.get(id=int(request.data['contract_id']))
    if contract.user != user:
        raise ValidationError({'result': 'Wrong token'}, code=404)
    if contract.contract_type != 40:
        raise ValidationError({'result': 'Wrong contract id'}, code=404)
    contract.invisible = True
    contract.save()
    return Response('Contract with id {id} deleted'.format(id=contract.id))


@api_view(http_method_names=['GET'])
def get_near_contracts(request):
    '''
    get info about all user's near contracts
    :param request: token, network_id
    :return: balance
    '''
    if request.user.is_anonymous:
        return HttpResponse(status=403)
    user = request.user
    if 'limit' in request.data:
        limit = int(request.data['limit'])
    else:
        limit = 8
    contracts = Contract.objects.filter(contract_type=40,
                                        user=user,
                                        network__name__in=['NEAR_MAINNET', 'NEAR_TESTNET'],
                                        invisible=False)
    contracts = contracts.order_by('-created_date')[0:limit]
    answer = {'contracts': []}
    for c in contracts:
        contract_info = {
            'contract_id': c.id,
            'state': c.state,
            'created_date': c.created_date,
            'network': c.network.name,
            'network_id': c.network.id,
            'name': c.name,
            'details': ContractDetailsNearTokenSerializer(c.get_details()).data
        }
        answer['contracts'].append(contract_info)
    return JsonResponse(answer)
