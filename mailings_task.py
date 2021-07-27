from datetime import datetime, timedelta
from celery_config import app

from django.db import OperationalError
from django.core.mail import send_mail

from lastwill.contracts.models import Contract
from lastwill.profile.models import UserSiteBalance
from lastwill.payments.api import positive_payment
from lastwill.settings import WISH_GIFT_AMOUNT, SEND_GIFT_MAIL_DAYS
from email_messages import testnet_wish_gift_subject, remind_balance_subject, testnet_gift_reminder_message


@app.task
def send_gift_emails():
    delta = timedelta(days=SEND_GIFT_MAIL_DAYS)
    testnet_contracts = Contract.objects.filter(deployed_at__gte=datetime.now() - delta).exclude(
        network__name__contains='MAINNET')
    users = list(set(contract.user for contract in testnet_contracts))

    for idx, user in enumerate(users):
        user_contracts = user.contract_set.all()
        for contract in user_contracts:
            if 'MAINNET' in contract.network.name:
                users.pop(idx)
                continue

    try:
        for user in users:
            profile = user.profile
            if not profile.received_gift:
                if user.email:
                    amount = WISH_GIFT_AMOUNT * 10 ** 18
                    positive_payment(user, amount, site_id=1)
                    profile.received_gift = True
                    profile.save()
                    send_mail(subject=testnet_wish_gift_subject,
                              message='',
                              from_email='support@mywish.io',
                              recipient_list=[user.email],
                              html_message=testnet_gift_reminder_message)
    except OperationalError:
        pass


@app.task
def remind_balance():
    users_balances = UserSiteBalance.objects.filter(subsite_id=1).filter(balance__gt=0)
    users = list(set(balance.user for balance in users_balances))

    for idx, user in enumerate(users):
        if not user.profile.received_gift:
            users.pop(idx)
            continue
        user_contracts = user.contract_set.all()
        for contract in user_contracts:
            if 'MAINNET' in contract.network.name:
                users.pop(idx)
                continue

    for user in users:
        if user.email:
            send_mail(subject=remind_balance_subject,
                      message='',
                      from_email='support@mywish.io',
                      recipient_list=[user.email],
                      html_message=testnet_gift_reminder_message)
