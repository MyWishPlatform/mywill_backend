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
from lastwill.contracts.api import *
from lastwill.contracts.api_eos import *
from lastwill.contracts.api_eth import *
from lastwill.contracts.models import *
from lastwill.contracts.submodels.near.token import init_account
from lastwill.deploy.models import *
from lastwill.profile.models import *
from lastwill.settings import MY_WISH_URL


@login_required
@api_view(http_method_names=['POST', 'GET'])
def deploy_near_contract(request, id=None):
    '''
    view for deploy near token
    :param request: contain contract_id, promo
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
        return HttpResponse(status=200)

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

    original_cost = contract.cost
    currency = 'USDT'
    site_id = 1
    network = contract.network.name
    promo_str = request.data.get('promo', None)
    if promo_str:
        promo_str = promo_str.upper()
    promo_str = check_error_promocode(promo_str, contract.contract_type) if promo_str else None
    cost = check_promocode(promo_str, request.user, original_cost, contract, contract_details)
    create_payment(request.user.id, '', currency, -cost, site_id, network)
    if promo_str:
        promo = Promo.objects.get(promo_str=promo_str.upper())
        User2Promo(user=request.user, promo=promo, contract_id=contract.id).save()
        promo.referral_bonus_usd += original_cost // NET_DECIMALS['USDT']
        promo.use_count += 1
        promo.save()

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
