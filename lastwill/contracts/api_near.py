from http import HTTPStatus
from xmlrpc.client import ResponseError

import near_api
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
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


@login_required
@api_view(http_method_names=['POST', 'GET'])
def deploy_near_contract(request, id):
    '''
    view for deploy near token
    :param request: contain contract id
    :return: id, state
    '''
    # Костыль для быстрого ответа фронту
    if request.method == 'GET':
        try:
            contract = Contract.objects.get(id=id)
        except ObjectDoesNotExist:
            return HttpResponse(status=404)
        if contract.invisible:
            raise ValidationError({'result': 'Contract is deleted'}, code=404)
        contract_details = contract.get_details()
        response = {
            'state': contract.state,
            'admin_address': contract_details.admin_address,
            'deploy_address': contract_details.deploy_address,
            'token_short_name': contract_details.token_short_name,
            'token_name': contract_details.token_name,
            'contract_id': contract.id,
            'token_type': contract_details.token_type,
            'decimals': contract_details.decimals,
            'future_minting': contract_details.future_minting,
            'total_supply': contract_details.maximum_supply,
        }
        return JsonResponse(response)

    user = request.user
    try:
        contract = Contract.objects.get(id=int(request.data.get('contract_id')))
    except ObjectDoesNotExist:
        return HttpResponse(status=404)
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
    contract.deploy_started_at = timezone.now()
    contract.save()

    response = {
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
    }

    # деплоим напрямую, сканера нет
    try:
        contract_details.deploy()
    except Exception:
        traceback.print_exc()
        contract.state = 'POSTPONED'
        contract.save()
        return JsonResponse(response)
    # проверяем успешность деплоя
    try:
        contract_details.initialized()
    except Exception:
        traceback.print_exc()
        contract.state = 'POSTPONED'
        contract.save()
        return JsonResponse(response)
    return JsonResponse(response)
