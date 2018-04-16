from ethereum import abi
import binascii
import datetime
import time
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()
from django.utils import timezone
from django.core.mail import send_mail
from lastwill.contracts.models import Contract, blocking
from lastwill.parint import *
from lastwill.settings import SIGNER, DEFAULT_FROM_EMAIL
import email_messages


def check_one(contract):

    contract.get_details().check_contract()


def check_all():
    print('check_all method', flush=True)
    for contract in Contract.objects.filter(contract_type__in=(0,1,4)):
        if contract.next_check:
            if contract.next_check <= timezone.now():
                print('checking contract', contract.id, flush=True)
                check_one(contract)
        send_reminders(contract)
       # carry_out_lastwillcontract(contract)
    print('checked all', flush=True)


def send_reminders(contract):
    if contract.contract_type == 0:
        details = contract.get_details()
        if contract.state == 'ACTIVE' and contract.user.email:
            if details.next_check:
                now = timezone.now()
                delta = details.next_check - now
                if delta.days <= 1:
                    print('1 day message', contract.id, flush=True)
                    send_mail(
                        email_messages.remind_subject,
                        email_messages.remind_message.format(days=1),
                        DEFAULT_FROM_EMAIL,
                        [contract.user.email]
                    )
                if delta.days == 5:
                    print('5 days message', contract.id, flush=True)
                    send_mail(
                        email_messages.remind_subject,
                        email_messages.remind_message.format(days=5),
                        DEFAULT_FROM_EMAIL,
                        [contract.user.email]
                    )
                if delta.days == 10:
                    print('10 days message', contract.id, flush=True)
                    send_mail(
                        email_messages.remind_subject,
                        email_messages.remind_message.format(days=10),
                        DEFAULT_FROM_EMAIL,
                        [contract.user.email]
                    )


if __name__ == '__main__':
    while 1:
        check_all()
        # time.sleep(60 * 60 * 24)
        time.sleep(60 * 10)

