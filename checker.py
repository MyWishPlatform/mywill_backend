import time
import pika
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django

django.setup()

from django.utils import timezone
from django.core.mail import send_mail

from lastwill.contracts.models import Contract
from lastwill.parint import *
from lastwill.settings import DEFAULT_FROM_EMAIL, LASTWILL_ALIVE_TIMEOUT
import email_messages
import datetime


def check_all():
    print('check_all method', flush=True)
    for contract in Contract.objects.filter(
            contract_type__in=(0, 1, 2, 18, 19, 23), state='ACTIVE'
    ):
        print('contract_id=', contract.id, flush=True)
        details = contract.get_details()
        print('details_id=', details.id, flush=True)
        if contract.contract_type == 2:
            # if details.date < timezone.now():
            #     send_in_pika(contract)
            pass
        elif contract.contract_type == 23:
            print('days for execution', (datetime.datetime.fromtimestamp(
                    details.end_timestamp) - timezone.now()).days, flush=True)
            if (datetime.datetime.fromtimestamp(
                    details.end_timestamp) - timezone.now()).days == 7 and not details.week_mail_sent:
                details.execution_before_mail(7)
            elif (datetime.datetime.fromtimestamp(
                    details.end_timestamp) - timezone.now()).days == 1 and not details.day_mail_sent:
                details.execution_before_mail(1)

            if details.end_timestamp < timezone.now().timestamp():
                try:
                    details.execute_contract()
                    print(contract.id, 'executed', flush=True)
                except:
                    print(contract.id, 'execution failed', flush=True)
        else:
            try:
                if details.active_to < timezone.now():
                    contract.state = 'EXPIRED'
                    contract.save()
                elif details.next_check and details.next_check <= timezone.now():
                    send_in_pika(contract)
                send_reminders(contract)
            except:
                print('fail', flush=True)
    print('checked all', flush=True)


def create_reminder(contract, day):
    day = 1 if day <= 1 else day
    print('{days} day message'.format(days=day), contract.id, flush=True)
    send_mail(
        email_messages.remind_subject,
        email_messages.remind_message.format(days=day),
        DEFAULT_FROM_EMAIL,
        [contract.user.email]
    )


def send_reminders(contract):
    if contract.contract_type in [0, 18, 19]:
        details = contract.get_details()
        if contract.state == 'ACTIVE' and contract.user.email:
            if details.next_check:
                now = timezone.now()
                delta = details.next_check - now
                if delta.days <= 1 or delta.days in {5, 10}:
                    create_reminder(contract, delta.days)


def send_in_pika(contract):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost',
        5672,
        'mywill',
        pika.PlainCredentials('java', 'java'),
    ))
    queue = NETWORKS[contract.network.name]['queue']
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True,
                          auto_delete=False,
                          exclusive=False)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps(
            {'status': 'COMMITTED', 'contractId': contract.id}),
        properties=pika.BasicProperties(type='check_contract'),
    )
    print('send check contract')
    connection.close()


if __name__ == '__main__':
    while 1:
        check_all()
        time.sleep(LASTWILL_ALIVE_TIMEOUT)
        # time.sleep(60 * 10)
