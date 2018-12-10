from django.contrib.auth.models import User
from django.db.models import F

from rest_framework.exceptions import ValidationError

from lastwill.payments.models import InternalPayment, FreezeBalance
from lastwill.profile.models import Profile, UserSiteBalance, SubSite
from lastwill.settings import MY_WISH_URL
from exchange_API import to_wish, convert


def create_payment(uid, tx, currency, amount, site_id):
    amount = float(amount)
    if amount == 0.0:
        return
    print('create payment')
    user = User.objects.get(id=uid)
    if SubSite.objects.get(id=site_id).site_name == MY_WISH_URL:
        value = amount if currency == 'WISH' else to_wish(
            currency, amount
        )
        if currency == 'BTC':
            value = value * 10 ** 18 / 10 ** 8
    else:
        if currency in ['ETH']:
            amount = amount / 10 ** 18
        if currency in ['BTC']:
            amount = amount / 10 ** 8
        value = amount if currency == 'EOSISH' else amount * convert(currency, 'EOSISH')['EOSISH']
        if value > 0.0:
            value = value * 10 ** 4
        if currency in ['ETH']:
            amount = amount * 10 ** 18
        if currency in ['BTC']:
            amount = amount * 10 ** 8

    if amount < 0.0:
        negative_payment(user, -value, site_id)
    else:
        positive_payment(user, value, site_id, currency)
    site = SubSite.objects.get(id=site_id)
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


def positive_payment(user, value, site_id, currency):
    UserSiteBalance.objects.select_for_update().filter(
        user=user, subsite__id=site_id).update(
            balance=F('balance') + value)
    if site_id == 1:
        FreezeBalance.objects.select_for_update().filter(id=1).update(
            wish=F('wish') + value * 0.15
        )
    else:
        if currency not in ['EOS', 'EOSISH']:
            FreezeBalance.objects.select_for_update().filter(id=1).update(
                eosish=F('eosish') + (value * 0.15) * 10 ** 4
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
