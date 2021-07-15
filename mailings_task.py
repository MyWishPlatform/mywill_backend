from datetime import datetime, timedelta
from celery_config import app
from django.db import transaction, OperationalError
from django.core.mail import send_mail


from lastwill.contracts.models import Contract
from lastwill.profile.models import UserSiteBalance


@app.task
def send_emails():
    contracts = Contract.objects.filter(deployed_at__gte=datetime.now() - timedelta(days=3))\
        .exclude(network__name__contains='MAINNET')
    testnet_users = [contract.user for contract in contracts]

    for idx, user in enumerate(testnet_users):
        user_contracts = user.contract_set.all()
        for contract in user_contracts:
            if 'MAINNET' in contract.network.name:
                testnet_users.pop(idx)

    try:
        for user in testnet_users:
            with transaction.atomic():
                user_balance = UserSiteBalance.objects.select_for_uodate()\
                    .filter(user__id=user.id).filter(subsite_id=1)
                if not user_balance.received_gift:
                    user_balance += amount * 10 ** 18
                    user_balance.save()
                    send_mail()
    except OperationalError:
        pass


@app.task
def remind_balance():
    users_balances = UserSiteBalance.objects.filter(subsite_id=1).filter(balance__gt=0)
    users = list(set(balance.user for balance in users_balances))

    for idx, user in enumerate(users):
        user_contracts = user.contract_set.all()
        for contract in user_contracts:
            if 'MAINNET' in contract.network.name:
                users.pop(idx)


    for user in users:
        send_mail()
