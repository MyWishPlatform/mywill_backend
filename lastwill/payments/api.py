import datetime

from django.contrib.auth.models import User
from django.db.models import F

from rest_framework.exceptions import ValidationError

from lastwill.payments.models import InternalPayment, FreezeBalance
from lastwill.profile.models import Profile, UserSiteBalance, SubSite
from lastwill.settings import MY_WISH_URL, TRON_URL
from lastwill.consts import NET_DECIMALS
from exchange_API import to_wish, convert


def create_payment(uid, tx, currency, amount, site_id):
    amount = float(amount)
    if amount == 0.0:
        return
    print('create payment')
    if SubSite.objects.get(id=site_id).site_name in (MY_WISH_URL, TRON_URL):
        value = amount if currency == 'WISH' else to_wish(
            currency, amount
        )
        if currency == 'BTC':
            value = value * NET_DECIMALS['ETH'] / NET_DECIMALS['BTC']
    else:
        amount = calculate_decimals(currency, amount)
        value = amount if currency == 'EOSISH' else amount * convert(currency, 'EOSISH')['EOSISH'] * NET_DECIMALS['EOSISH']
        amount = add_decimals(currency, amount)
    user = User.objects.get(id=uid)
    if amount < 0.0:
        negative_payment(user, -value, site_id)
    else:
        positive_payment(user, value, site_id, currency)
    site = SubSite.objects.get(id=site_id)
    InternalPayment(
        user_id=uid,
        delta=value,
        tx_hash=tx,
        original_currency=currency,
        original_delta=str(amount),
        site=site
    ).save()
    print('payment created')


def calculate_decimals(currency, amount):
    # count sum payments without decimals
    if currency in ['ETH']:
        amount = amount / NET_DECIMALS['ETH']
    if currency in ['BTC']:
        amount = amount / NET_DECIMALS['BTC']
    if currency in ['EOS']:
        amount = amount / NET_DECIMALS['EOS']
    return amount


def add_decimals(currency, amount):
    # add decimals for eth, btc
    if currency in ['ETH']:
        amount = amount * NET_DECIMALS['ETH']
    if currency in ['BTC']:
        amount = amount * NET_DECIMALS['BTC']
    return amount


def positive_payment(user, value, site_id, currency):
    UserSiteBalance.objects.select_for_update().filter(
        user=user, subsite__id=site_id).update(
            balance=F('balance') + value)
    if site_id == 1:
        FreezeBalance.objects.select_for_update().filter(id=1).update(
            wish=F('wish') + value * 0.15
        )
    else:
        FreezeBalance.objects.select_for_update().filter(id=1).update(
            eosish=F('eosish') + (value * 0.15)
        )

def negative_payment(user, value, site_id):
    if not UserSiteBalance.objects.select_for_update().filter(
            user=user, subsite__id=site_id, balance__gte=value
    ).update(balance=F('balance') - value):
        raise ValidationError({'result': 3}, code=400)


def get_payment_statistics(start, stop=None):
    if not stop:
        stop = datetime.datetime.now().date()
    payments = InternalPayment.objects.filter(
        delta__gte=0, datetime__gte=start, datetime__lte=stop
    )
    total_payments = {'ETH': 0.0, 'WISH': 0.0, 'BTC': 0.0, 'BNB': 0.0, 'EOS': 0.0, 'EOSISH': 0.0}
    for pay in payments:
        print(
            pay.datetime.date(),
            pay.user,
            float(pay.original_delta)/NET_DECIMALS[pay.original_currency],
            pay.original_currency,
            flush=True
        )
        total_payments[pay.original_currency] += float(pay.original_delta)/NET_DECIMALS[pay.original_currency]

    print('total_payments', total_payments, flush=True)
