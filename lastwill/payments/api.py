import requests

from django.contrib.auth.models import User
from django.db.models import F

from lastwill.payments.models import InternalPayment
from lastwill.profile.models import Profile, UserSiteBalance, SubSite
from lastwill.settings import test_logger
from exchange_API import to_wish, convert


def create_payment(uid, tx, currency, amount, site_id):
    amount = float(amount)
    if amount == 0.0:
        return
    print('create payment')
    user = User.objects.get(id=uid)
    if SubSite.objects.get(id=site_id).site_name == 'dev.mywish.io':
        value = amount if currency == 'WISH' else to_wish(
            currency, amount
        )
    else:
        if currency in ['ETH', 'BTC']:
            amount = amount / 10 ** 18
        value = amount * convert(currency, 'EOSISH')['EOSISH']

    if amount < 0.0:
        negative_payment(user, -value, site_id)
    else:
        positive_payment(user, value, site_id)
    site = SubSite.objects.get(id = site_id)
    payment = InternalPayment(
        user_id=uid,
        delta=value,
        tx_hash=tx,
        original_currency=currency,
        original_delta=str(amount),
        site=site
    )
    payment.save()
    print('payment created')


def positive_payment(user, value, site_id):
    UserSiteBalance.objects.select_for_update().filter(
        user=user, subsite__id=site_id).update(
            balance=F('balance') + value)


def negative_payment(user, value, site_id):
    if not UserSiteBalance.objects.select_for_update().filter(
            user=user, subsite__id=site_id, balance__gte=value
    ).update(balance=F('balance') - value):
        raise Exception('no money')
