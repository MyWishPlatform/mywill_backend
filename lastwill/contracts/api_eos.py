from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from lastwill.contracts.serializers import *
from lastwill.contracts.models import *


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
    answer = {'state': contract.state, 'address': contract_details.token_account}
    answer['decimals'] = contract_details.decimals
    answer['admin_address'] = contract_details.admin_address
    answer['token_short_name'] = contract_details.token_short_name
    if contract_details.eos_contract.tx_hash:
        answer['tx_hash'] = contract_details.eos_contract.tx_hash
    return JsonResponse(answer)


@api_view()
def create_eos_account(request):
    '''
    view for create eos account
    :param request: contain account_name, owner_public_key, active_public_key
    :return: ok
    '''
    network = Network.objects.get(id=10)
    contract = Contract(
        state='CREATED',
        name='Contract',
        contract_type=11,
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
    token_params['account_name'] = request.query_params['account_name']
    token_params['owner_public_key'] = request.query_params['owner_public_key']
    token_params['active_public_key'] = request.query_params['active_public_key']
    token_params['stake_net_value'] = request.query_params['stake_net_value'] if request.query_params['stake_net_value'] else '0.01'
    token_params['stake_cpu_value'] = request.query_params['stake_cpu_value'] if request.query_params['stake_cpu_value'] else '0.64'
    token_params['buy_ram_kbytes'] = int(request.query_params['buy_ram_kbytes']) if request.query_params['buy_ram_kbytes'] else 4
    token_params['eos_contract'] = eos_contract
    ContractDetailsEOSAccountSerializer().create(contract, token_params)
    return Response('ok')


@api_view()
def deploy_eos_account(request):
    '''
    view for deploy eos ac count
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
