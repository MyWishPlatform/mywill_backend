from django.contrib.auth.models import User
from django.db.models import F

from lastwill.payments.models import InternalPayment
from lastwill.profile.models import Profile


def create_payment(uid, value, tx, currency, amount, update=True):
    if value == 0.0:
        return
    print('create payment')
    user = User.objects.get(id=uid)

    if update:
        Profile.objects.select_for_update().filter(id=user.profile.id).update(
        balance=F('balance') + value)

    payment = InternalPayment(
        user_id=uid,
        delta=value,
        tx_hash=tx,
        original_currency=currency,
        original_delta=amount
    )
    payment.save()
