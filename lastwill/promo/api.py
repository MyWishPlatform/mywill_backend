import datetime
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import *

def check_and_get_discount(promo_str, contract_type, user):
    promo = Promo.objects.filter(promo_str=promo_str.upper()).first()
    if promo is None:
        raise PermissionDenied(2000)
    now = datetime.datetime.now()
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
    user = request.user
    contract_type = request.query_params['contract_type']
    promo_str = request.query_params['promo']
    discount = check_and_get_discount(promo_str, contract_type, user)
    return Response({'discount': discount})
