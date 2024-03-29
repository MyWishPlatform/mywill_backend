import datetime
import random
import string

from lastwill.promo.models import Promo, Promo2ContractType


def id_generator(size=10):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=size))


def create_promocode(contract_types,
                     discount,
                     reusable=False,
                     start=None,
                     stop=None,
                     use_count=0,
                     use_count_max=None,
                     promo_str=None):
    if not promo_str:
        promo_str = id_generator(size=8)
    print(promo_str)
    promo = Promo.objects.filter(promo_str=promo_str).first()
    if promo is not None:
        print('this promocode already exists')
        return
    else:
        if start is None and stop is None:
            start = datetime.datetime.now().date()
            stop = datetime.datetime(start.year + 1, start.month, start.day).date()
        promo = Promo(
            promo_str=promo_str,
            start=start,
            stop=stop,
            use_count=use_count,
            use_count_max=use_count_max,
            reusable=reusable,
        )
        promo.save()
        for ct in contract_types:
            p2c = Promo2ContractType(promo=promo, discount=discount, contract_type=ct)
            p2c.save()
            print(promo_str)
        return promo_str
