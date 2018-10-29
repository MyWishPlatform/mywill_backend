from django.http import JsonResponse
from django.contrib.auth.models import User

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from lastwill.contracts.serializers import *
from lastwill.contracts.models import *


@api_view(http_method_names=['POST'])
def create_eos_token(request):
    '''
    view for create eos token
    :param request: contain token_short_name, token_account,
    decimals, maximum_supply, user_id
    :return: ok
    '''
    user = User.objects.filter(id=request.data['user_id']).first()
    if not user:
        raise ValidationError({'result': 'Invalid user id'}, code=404)
    network = Network.objects.get(id=10)
    contract = Contract(
        state='CREATED',
        name='Contract',
        contract_type=14,
        network=network,
        cost=0,
        user=user
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
    token_params['decimals'] = int(request.data['decimals'])
    token_params['maximum_supply'] = int(request.data['maximum_supply'])
    token_params['token_short_name'] = request.data['token_short_name']
    token_params['token_account'] = request.data['token_account']
    token_params['admin_address'] = request.data['admin_address']
    token_params['eos_contract'] = eos_contract
    ContractDetailsEOSTokenSASerializer().create(contract, token_params)
    return Response('ok')


@api_view(http_method_names=['POST'])
def deploy_eos_token(request):
    '''
    view for deploy eos token
    :param request: contain contract id
    :return:
    '''
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.state != 'CREATED':
        raise ValidationError({'result': 'Wrong state'}, code=404)
    contract_details = contract.get_details()
    contract_details.predeploy_validate()
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.save()
    queue = NETWORKS[contract.network.name]['queue']
    send_in_queue(contract.id, 'launch', queue)
    return Response('ok')


@api_view(http_method_names=['GET'])
def show_eos_token(request):
    '''
    view for show eos token
    :param request: contain contract id
    :return:
    '''
    contract = Contract.objects.get(id=request.query_params.get('id'))
    contract_details = contract.get_details()
    answer = {'state': contract.state, 'address': contract_details.token_account}
    answer['decimals'] = contract_details.decimals
    answer['admin_address'] = contract_details.admin_address
    answer['token_short_name'] = contract_details.token_short_name
    if contract_details.eos_contract.tx_hash:
        answer['tx_hash'] = contract_details.eos_contract.tx_hash
    return JsonResponse(answer)


@api_view(http_method_names=['PUT, PATCH'])
def edit_eos_token(request):
    '''
    view for edit params in  eos token
    :param request: contain contract id, editable field
    (decimals, max_supply, addresses or token_short_name)
    :return:
    '''
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.state != 'CREATED':
        raise ValidationError({'result': 2}, code=403)
    contract_details = contract.get_details()
    if 'decimals' in request.data:
        contract_details.decimals = int(request.data['decimals'])
    if 'maximum_supply' in request.data:
        contract_details.maximum_supply = int(request.data['maximum_supply'])
    if 'token_short_name' in request.data:
        contract_details.token_short_name = request.data['token_short_name']
    if 'token_account' in request.data:
        contract_details.token_account = request.data['token_account']
    if 'admin_address' in request.data:
        contract_details.admin_address = request.data['admin_address']
    contract_details.save()
    return Response('ok')


@api_view(http_method_names=['POST'])
def create_eos_account(request):
    '''
    view for create eos account
    :param request: contain account_name, owner_public_key, active_public_key, user_id
    :return: ok
    '''
    user = User.objects.filter(id=request.data['user_id']).first()
    if not user:
        raise ValidationError({'result': 'Invalid user id'}, code=404)
    network = Network.objects.get(id=10)
    contract = Contract(
        state='CREATED',
        name='Contract',
        contract_type=11,
        network=network,
        cost=0,
        user=user
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
    token_params['account_name'] = request.data['account_name']
    token_params['owner_public_key'] = request.data['owner_public_key']
    token_params['active_public_key'] = request.data['active_public_key']
    if 'stake_net_value' in request.data:
        token_params['stake_net_value'] = request.data['stake_net_value']
    else:
        token_params['stake_net_value'] = '0.01'
    if 'stake_cpu_value' in  request.data:
        token_params['stake_cpu_value'] = request.data['stake_cpu_value']
    else:
        token_params['stake_cpu_value'] = '0.64'
    if 'buy_ram_kbytes' in request.data:
        token_params['buy_ram_kbytes'] = int(request.data['buy_ram_kbytes'])
    else:
        token_params['buy_ram_kbytes'] = 4
    token_params['eos_contract'] = eos_contract
    ContractDetailsEOSAccountSerializer().create(contract, token_params)
    return Response('ok')


@api_view(http_method_names=['POST'])
def deploy_eos_account(request):
    '''
    view for deploy eos ac count
    :param request: contain contract id
    :return:
    '''
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.state != 'CREATED':
        raise ValidationError({'result': 'Wrong state'}, code=404)
    contract_details = contract.get_details()
    contract_details.predeploy_validate()
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.save()
    queue = NETWORKS[contract.network.name]['queue']
    send_in_queue(contract.id, 'launch', queue)
    return Response('ok')


@api_view(http_method_names=['GET'])
def show_eos_account(request):
    '''
    view for show eos account
    :param request: contain contract id
    :return:
    '''
    contract = Contract.objects.get(id=request.query_params.get('id'))
    contract_details = contract.get_details()
    answer = {'state': contract.state, 'address': contract_details.account_name}
    answer['net'] = contract_details.stake_net_value
    answer['cpu'] = contract_details.stake_cpu_value
    answer['ram'] = contract_details.buy_ram_kbytes
    if contract_details.eos_contract.tx_hash:
        answer['tx_hash'] = contract_details.eos_contract.tx_hash
    return JsonResponse(answer)


@api_view(http_method_names=['PUT, PATCH'])
def edit_eos_account(request):
    '''
    view for edit params in  eos account
    :param request: contain contract id, editable field
    (account_name, public_key, cpu, net, ram)
    :return:
    '''
    contract = Contract.objects.get(id=request.data.get('id'))
    if contract.state != 'CREATED':
        raise ValidationError({'result': 2}, code=403)
    contract_details = contract.get_details()
    if 'stake_net_value' in request.data:
        contract_details.stake_net_value = int(request.data['stake_net_value'])
    if 'stake_cpu_value' in request.data:
        contract_details.stake_cpu_value = int(request.data['stake_cpu_value'])
    if 'buy_ram_kbytes' in request.data:
        contract_details.buy_ram_kbytes = request.data['buy_ram_kbytes']
    if 'account_name' in request.data:
        contract_details.account_name = request.data['account_name']
    if 'owner_public_key' in request.data:
        contract_details.owner_public_key = request.data['owner_public_key']
    if 'active_public_key' in request.data:
        contract_details.active_public_key = request.data['active_public_key']
    contract_details.save()
    return Response('ok')
