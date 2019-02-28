import datetime
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from lastwill.contracts.submodels.common import Contract
from lastwill.contracts.serializers import ContractSerializer
from lastwill.settings import  MY_WISH_URL, EOSISH_URL
from lastwill.consts import NET_DECIMALS
from exchange_API import *
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
    if promo.user2promo_set.filter(user=user).exists():
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
                contract.contract_type
            )().to_representation(contract_details)
            cost = contract_details.calc_cost_eos(kwargs, contract.network) * discount / 100
            answer['discount_price'] = {
                'EOS': cost,
                'EOSISH': str(float(cost) * convert('EOS', 'EOSISH')['EOSISH'])
            }
        elif host == MY_WISH_URL:
            cost = contract.cost * discount / 100
            if contract.contract_type == 5:
                print('token token', flush=True)
                if contract_details.authio:
                    print('token with authio', flush=True)
                    cost = (contract.cost - 3 * NET_DECIMALS['ETH']) * discount / 100 + 3 * NET_DECIMALS['ETH']
            answer['discount_price'] = {
            'ETH': str(cost),
            'WISH': str(int(to_wish('ETH', int(cost)))),
            'BTC': str(int(cost) * convert('ETH', 'BTC')['BTC']),
            'TRX': str(int(cost) / 10 ** 18 * convert('ETH', 'TRX')['TRX'] * 10 ** 6),
            'TRONISH': str(int(cost) / 10 ** 18 * convert('ETH', 'TRX')['TRX'] * 10 ** 6)
            }
        else:
            kwargs = ContractSerializer().get_details_serializer(
                contract.contract_type
            )().to_representation(contract_details)
            cost = contract_details.calc_cost(kwargs, contract.network) * discount / 100
            answer['discount_price'] = {
                'ETH': str(cost),
                'WISH': str(int(to_wish('ETH', int(cost)))),
                'BTC': str(int(cost) * convert('ETH', 'BTC')['BTC']),
                'TRX': str(int(cost) / 10 ** 18 * convert('ETH', 'TRX')[
                    'TRX'] * 10 ** 6),
                'TRONISH': str(int(cost) / 10 ** 18 * convert('ETH', 'TRX')[
                    'TRX'] * 10 ** 6)
            }

    return Response(answer)


def create_promocode(
        promo_str, contract_types, discount, start=None,
        stop=None, use_count=0, use_count_max=None
):
    promo = Promo.objects.filter(promo_str=promo_str.upper()).first()
    if promo is not None:
        print('this promocode already exists')
        return
    else:
        if start is None and stop is None:
            start = datetime.datetime.now().date()
            stop = datetime.datetime(start.year+1, start.month, start.day).date()
        promo = Promo(
            promo_str=promo_str, start=start, stop=stop,
            use_count=use_count, use_count_max = use_count_max
        )
        promo.save()
        for ct in contract_types:
            p2c = Promo2ContractType(
                promo=promo, discount=discount, contract_type=ct
            )
            p2c.save()
        return promo
