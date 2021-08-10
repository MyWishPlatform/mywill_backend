from celery import shared_task

from django.db import OperationalError
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction

from lastwill.profile.models import Profile
from lastwill.profile.models import SubSite
from lastwill.payments.models import InternalPayment
from lastwill.payments.api import positive_payment
from lastwill.settings import WISH_GIFT_AMOUNT, SEND_GIFT_MAIL_DAYS, DEFAULT_SUPPORT_EMAIL, DEFAULT_SUPPORT_PASSWORD
from email_messages import testnet_wish_gift_subject, remind_balance_subject, testnet_gift_reminder_message


@shared_task
@transaction.atomic
def send_testnet_gift_emails(profile_id):
    contracts = User.objects.get(profile__id=profile_id).contract_set.all()
    if 'MAINNET' in [contract.network.name for contract in contracts]:
        return
    try:
        profile = Profile.objects.select_for_update() \
            .filter(id=profile_id).filter(wish_bonus_received=False)[0]

        user = profile.user
        site = SubSite.objects.get(id=1)

        value = WISH_GIFT_AMOUNT * 10 ** 18

        positive_payment(user, value, currency='WISH', amount=WISH_GIFT_AMOUNT, site_id=1)
        profile.wish_bonus_received = True
        profile.save()

        InternalPayment(
            user_id=user.id,
            delta=value,
            original_currency='WISH',
            original_delta=str(WISH_GIFT_AMOUNT),
            fake=True,
            site=site).save()

        send_mail(subject=testnet_wish_gift_subject,
                  message='',
                  from_email=DEFAULT_SUPPORT_EMAIL,
                  recipient_list=[user.email],
                  html_message=testnet_gift_reminder_message,
                  auth_user=DEFAULT_SUPPORT_EMAIL,
                  auth_password=DEFAULT_SUPPORT_PASSWORD)

    except OperationalError:
        pass


@shared_task
def remind_balance():
    users = list(User.objects.filter(profile__wish_bonus_received=True) \
                 .filter(usersitebalance__balance__gt=0) \
                 .filter(usersitebalance__subsite=1))

    for idx, user in enumerate(users):
        user_contracts = user.contract_set.all()
        for contract in user_contracts:
            if 'MAINNET' in contract.network.name:
                users.pop(idx)
                continue

    for user in users:
        if user.email:
            send_mail(subject=remind_balance_subject,
                      message='',
                      from_email=DEFAULT_SUPPORT_EMAIL,
                      recipient_list=[user.email],
                      html_message=testnet_gift_reminder_message,
                      auth_user=DEFAULT_SUPPORT_EMAIL,
                      auth_password=DEFAULT_SUPPORT_PASSWORD)
