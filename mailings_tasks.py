import traceback
import sys

from time import sleep

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
from email_messages import testnet_wish_gift_subject, remind_balance_subject, testnet_gift_reminder_message, \
    mainnet_created_subject, mainnet_created_message


@shared_task
@transaction.atomic
def send_testnet_gift_emails(profile_id):
    contracts = User.objects.get(profile__id=profile_id).contract_set.all()
    deployed_contracts = contracts.exclude(state__in=('CREATED',
                                                      'WAITING_FOR_DEPLOYMENT',
                                                      'WAITING_FOR_PAYMENT',
                                                      'POSTPONED',
                                                      'TIME_IS_UP'))
    for contract in deployed_contracts:
        if 'MAINNET' in contract.network.name:
            return
    try:
        profile = Profile.objects.select_for_update().get(id=profile_id)
        if not profile.wish_bonus_received:
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
                site=site
            ).save()

            send_mail(subject=testnet_wish_gift_subject,
                      message='',
                      from_email=DEFAULT_SUPPORT_EMAIL,
                      recipient_list=[user.email],
                      html_message=testnet_gift_reminder_message,
                      auth_user=DEFAULT_SUPPORT_EMAIL,
                      auth_password=DEFAULT_SUPPORT_PASSWORD)
            print(f'sent gift email to user id: {user.id} {user.email}')
    except OperationalError:
        print('an error occurred while sending gift email')
        print('\n'.join(traceback.format_exception(*sys.exc_info())))
        pass


@shared_task
def remind_balance():
    users = list(User.objects.filter(profile__wish_bonus_received=True) \
                 .exclude(email__exact='') \
                 .filter(usersitebalance__balance__gt=0) \
                 .filter(usersitebalance__subsite=1))

    filtered_users = []
    for user in users:
        negative_payments = user.internalpayment_set.all().filter(delta__lt=0)
        if not negative_payments:
            filtered_users.append(user)

    for user in filtered_users:
        send_mail(subject=remind_balance_subject,
                  message='',
                  from_email=DEFAULT_SUPPORT_EMAIL,
                  recipient_list=[user.email],
                  html_message=testnet_gift_reminder_message,
                  auth_user=DEFAULT_SUPPORT_EMAIL,
                  auth_password=DEFAULT_SUPPORT_PASSWORD)
        print(f'sent reminder email to user id: {user.id} {user.email}')
        sleep(60)


@shared_task
def send_promo_mainnet(user_email):
    send_mail(subject=mainnet_created_subject,
              message='',
              from_email=DEFAULT_SUPPORT_EMAIL,
              recipient_list=[user_email],
              html_message=mainnet_created_message,
              auth_user=DEFAULT_SUPPORT_EMAIL,
              auth_password=DEFAULT_SUPPORT_PASSWORD)
    print(f'sent promo email to user id: {user_email}')
