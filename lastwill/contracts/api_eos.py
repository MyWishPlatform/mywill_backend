import hashlib
import hmac

from django.http import JsonResponse
from django.contrib.auth.models import User

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from lastwill.contracts.serializers import *
from lastwill.contracts.models import *
from lastwill.other.models import *


def check_auth(user_id, user_secret_key, params):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise ValidationError({'result': 'Invalid user id'}, code=404)
    ex_service = ExternalService.objects.filter(user=user).first()
    if not ex_service:
        raise ValidationError({'result': 'This service is not allowed'}, code=404)
    str_params = '?' + '&'.join([k + '=' + v for k, v in params.items()])
    hash = hmac.new(
        ex_service.secret.encode(),
        (ex_service.old_hmac + str_params).encode(),
        hashlib.sha256
    )
    secret_key = hash.hexdigest()
    if secret_key == user_secret_key:
        ex_service.old_hmac = secret_key
        ex_service.save()
        return True
    else:
        raise ValidationError({'result': 'Authorisation Error'}, code=404)


@api_view(http_method_names=['POST'])
def create_eos_token(request):
    '''
    view for create eos token
    :param request: contain token_short_name, token_account,
    decimals, maximum_supply, user_id
    :return: ok
    '''
    user_id = int(request.data['user_id'])
    user_secret_key = request.data['secret_key']
    if not user_secret_key:
        raise ValidationError({'result': 'Secret key not found'}, code=404)
    check_auth(user_id, user_secret_key, request.data)
    network = Network.objects.get(id=10)
    contract = Contract(
        state='CREATED',
        name='Contract',
        contract_type=14,
        network=network,
        cost=0,
        user_id=user_id
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
    user_id = int(request.data['user_id'])
    user_secret_key = request.data['secret_key']
    if not user_secret_key:
        raise ValidationError({'result': 'Secret key not found'}, code=404)
    check_auth(user_id, user_secret_key, request.data)
    contract = Contract.objects.get(id=int(request.data.get('id')))
    if contract.state != 'CREATED':
        raise ValidationError({'result': 'Wrong state'}, code=404)
    contract_details = contract.get_details()
    contract_details.predeploy_validate()
    contract.state = 'WAITING_FOR_DEPLOYMENT'
    contract.save()
    # add withdraw coins
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
    user_id = int(request.query_params['user_id'])
    user_secret_key = request.query_params['secret_key']
    if not user_secret_key:
        raise ValidationError({'result': 'Secret key not found'}, code=404)
    check_auth(user_id, user_secret_key, request.query_params)
    contract = Contract.objects.get(id=int(request.query_params.get('id')))
    contract_details = contract.get_details()
    answer = {'state': contract.state, 'address': contract_details.token_account}
    answer['decimals'] = contract_details.decimals
    answer['admin_address'] = contract_details.admin_address
    answer['token_short_name'] = contract_details.token_short_name
    if contract_details.eos_contract.tx_hash:
        answer['tx_hash'] = contract_details.eos_contract.tx_hash
    return JsonResponse(answer)


@api_view(http_method_names=['PUT', 'PATCH'])
def edit_eos_token(request):
    '''
    view for edit params in  eos token
    :param request: contain contract id, editable field
    (decimals, max_supply, addresses or token_short_name)
    :return:
    '''
    user_id = int(request.data['user_id'])
    user_secret_key = request.data['secret_key']
    if not user_secret_key:
        raise ValidationError({'result': 'Secret key not found'}, code=404)
    check_auth(user_id, user_secret_key, request.data)
    contract = Contract.objects.get(id=int(request.data.get('id')))
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
    user_id = int(request.data['user_id'])
    user_secret_key = request.data['secret_key']
    if not user_secret_key:
        raise ValidationError({'result': 'Secret key not found'}, code=404)
    check_auth(user_id, user_secret_key, request.data)
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
    user_id = int(request.data['user_id'])
    user_secret_key = request.data['secret_key']
    if not user_secret_key:
        raise ValidationError({'result': 'Secret key not found'}, code=404)
    check_auth(user_id, user_secret_key, request.data)
    contract = Contract.objects.get(id=int(request.data.get('id')))
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
    user_id = int(request.query_params['user_id'])
    user_secret_key = request.query_params['secret_key']
    if not user_secret_key:
        raise ValidationError({'result': 'Secret key not found'}, code=404)
    check_auth(user_id, user_secret_key, request.query_params)
    contract = Contract.objects.get(id=int(request.query_params.get('id')))
    contract_details = contract.get_details()
    answer = {'state': contract.state, 'address': contract_details.account_name}
    answer['net'] = contract_details.stake_net_value
    answer['cpu'] = contract_details.stake_cpu_value
    answer['ram'] = contract_details.buy_ram_kbytes
    if contract_details.eos_contract.tx_hash:
        answer['tx_hash'] = contract_details.eos_contract.tx_hash
    return JsonResponse(answer)


@api_view(http_method_names=['PUT', 'PATCH'])
def edit_eos_account(request):
    '''
    view for edit params in  eos account
    :param request: contain contract id, editable field
    (account_name, public_key, cpu, net, ram)
    :return:
    '''
    user_id = int(request.data['user_id'])
    user_secret_key = request.data['secret_key']
    if not user_secret_key:
        raise ValidationError({'result': 'Secret key not found'}, code=404)
    check_auth(user_id, user_secret_key, request.data)
    params = json.loads(request.body)
    contract = Contract.objects.get(id=int(params['id']))
    if contract.state != 'CREATED':
        raise ValidationError({'result': 2}, code=403)
    contract_details = contract.get_details()
    if 'stake_net_value' in params:
        contract_details.stake_net_value = int(params['stake_net_value'])
    if 'stake_cpu_value' in params:
        contract_details.stake_cpu_value = int(params['stake_cpu_value'])
    if 'buy_ram_kbytes' in params:
        contract_details.buy_ram_kbytes = params['buy_ram_kbytes']
    if 'account_name' in params:
        contract_details.account_name = params['account_name']
    if 'owner_public_key' in params:
        contract_details.owner_public_key = params['owner_public_key']
    if 'active_public_key' in params:
        contract_details.active_public_key = params['active_public_key']
    contract_details.save()
    return Response('ok')
