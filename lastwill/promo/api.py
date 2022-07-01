import datetime

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from lastwill.consts import (AUTHIO_PRICE_USDT, NET_DECIMALS, VERIFICATION_PRICE_USDT)
from lastwill.contracts.serializers import ContractSerializer
from lastwill.contracts.submodels.common import Contract
from lastwill.rates.api import rate
from lastwill.settings import (EOSISH_URL, MY_WISH_URL, TRON_URL, VERIFICATION_CONTRACTS_IDS, WAVES_URL)

from .models import *


def check_and_get_discount(promo_str, contract_type, user):
    promo = Promo.objects.filter(promo_str=promo_str.upper()).first()
    if promo is None:
        raise PermissionDenied(2000)
    now = datetime.datetime.now().date()
    if (promo.start and promo.start > now) or (promo.stop and promo.stop < now):
        raise PermissionDenied(2003)
    if promo.use_count_max and promo.use_count >= promo.use_count_max:
        raise PermissionDenied(2004)
    if not promo.reusable and promo.user2promo_set.filter(user=user).exists():
        raise PermissionDenied(2001)
    p2ct = promo.promo2contracttype_set.filter(contract_type=contract_type).first()
    if not p2ct:
        raise PermissionDenied(2002)
    return p2ct.discount


@api_view()
def get_discount(request):
    if request.user.is_anonymous:
        raise PermissionDenied()
    host = request.META['HTTP_HOST']
    user = request.user
    contract_type = request.query_params['contract_type']
    promo_str = request.query_params['promo']
    discount = check_and_get_discount(promo_str, contract_type, user)
    answer = {'discount': discount}
    if 'contract_id' in request.query_params:
        contract = Contract.objects.get(id=request.query_params['contract_id'])
        contract_details = contract.get_details()
        if host == EOSISH_URL:
            kwargs = ContractSerializer().get_details_serializer(
                contract.contract_type)().to_representation(contract_details)
            cost = contract_details.calc_cost_eos(kwargs, contract.network) * (100 - discount) / 100
            answer['discount_price'] = {'EOS': cost, 'EOSISH': str(float(cost) * rate('EOS', 'EOSISH').value)}
        elif host == MY_WISH_URL:
            options_cost = 0
            if contract.contract_type in (5, 28) and contract_details.authio:
                options_cost += AUTHIO_PRICE_USDT * NET_DECIMALS['USDT']

            if contract.contract_type in VERIFICATION_CONTRACTS_IDS and contract_details.verification:
                options_cost += VERIFICATION_PRICE_USDT * NET_DECIMALS['USDT']

            cost = (contract.cost - options_cost) * (100 - discount) / 100 + options_cost
            answer['discount_price'] = {
                'USDT': str(cost),
                'ETH': str(int(int(cost) / 10**6 * rate('USDT', 'ETH').value * 10**18)),
                'WISH': str(int(int(cost) / 10**6 * rate('USDT', 'WISH').value * 10**18)),
                'BTC': str(int(int(cost) / 10**6 * rate('USDT', 'BTC').value * 10**8)),
                'TRX': str(int(int(cost) * rate('ETH', 'TRX').value)),
                'TRONISH': str(int(int(cost) * rate('ETH', 'TRX').value))
            }
        elif host == TRON_URL:
            kwargs = ContractSerializer().get_details_serializer(
                contract.contract_type)().to_representation(contract_details)
            cost = contract_details.calc_cost_tron(kwargs, contract.network) * (100 - discount) / 100

            answer['discount_price'] = {'TRX': int(cost), 'TRONISH': int(cost)}
        elif host == WAVES_URL:
            kwargs = ContractSerializer().get_details_serializer(
                contract.contract_type)().to_representation(contract_details)
            cost = contract_details.calc_cost(kwargs, contract.network) * (100 - discount) / 100
            answer['discount_price'] = {
                'USDT': str(cost),
                'ETH': str(int(int(cost) / 10**6 * rate('USDT', 'ETH').value * 10**18)),
                'WISH': str(int(int(cost) / 10**6 * rate('USDT', 'WISH').value * 10**18)),
                'BTC': str(int(int(cost) / 10**6 * rate('USDT', 'BTC').value * 10**8)),
                'TRX': str(int(int(cost) * rate('ETH', 'TRX').value)),
                'TRONISH': str(int(int(cost) * rate('ETH', 'TRX').value))
            }
        else:
            kwargs = ContractSerializer().get_details_serializer(
                contract.contract_type)().to_representation(contract_details)
            cost = contract_details.calc_cost(kwargs, contract.network) * (100 - discount) / 100
            answer['discount_price'] = {
                'ETH': str(cost),
                'WISH': str(int(cost * rate('ETH', 'WISH').value)),
                'BTC': str(int(cost * rate('ETH', 'BTC').value)),
                'TRX': str(int(cost) / 10**18 * rate('ETH', 'TRX').value * 10**6),
                'TRONISH': str(int(cost) / 10**18 * rate('ETH', 'TRONISH').value * 10**6)
            }

    return Response(answer)


def get_all_promos():
    count = 0
    for promo in Promo.objects.all():
        print('promo: ' + str(promo.promo_str),
              'start_date: ' + str(promo.start),
              'stop_date: ' + str(promo.stop),
              'used_times: ' + str(promo.use_count),
              'is_limited: ' + str(promo.use_count_max),
              '---------------',
              sep='\n')
        print()
        count += 1
    print('Promos total', count)


@api_view(http_method_names=['GET'])
def get_all_promos_api(request):
    count = 0

    promo_dict = {}
    for promo in Promo.objects.all():
        promo_dict[promo.promo_str] = {
            'promo': str(promo.promo_str),
            'start_date': str(promo.start),
            'stop_date': str(promo.stop),
            'used_times': str(promo.use_count),
            'is_limited': str(promo.use_count_max)
        }
        count += 1
    promo_dict['total'] = count

    return Response(promo_dict)
