import pika
import os
import sys
import traceback
import json
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()
from django.core.mail import send_mail
from django.utils import timezone

from lastwill.contracts.models import Contract
from lastwill.settings import DEFAULT_FROM_EMAIL
from lastwill.checker import check_one

QUEUE = 'notification'

def payment(message):
    print('payment message', flush=True)
    contract = Contract.objects.get(id=message['contractId'])
    if contract.state in ('CREATED', 'WAITING_FOR_PAYMENT') and message['balance'] > contract.cost:
        contract.deploy()
    print('payment ok', flush=True)

def deployed(message):
    print('deployed message received', flush=True)
    contract = Contract.objects.get(id=message['contractId'])
    contract.address = message['address']
    contract.state = 'ACTIVE'
    contract.next_check = timezone.now() + datetime.timedelta(seconds=contract.check_interval)
    contract.save()
    send_mail(
            'Contract deployed',
            'Contract deployed message',
            DEFAULT_FROM_EMAIL,
            [contract.user.email]
    )
    print('deployed ok!', flush=True)

def killed(message):
    print('killed message', flush=True)
    contract = Contract.objects.get(id=message['contractId'])
    contract.state = 'KILLED'
    contract.save()
    print('killed ok', flush=True)

def checked(message):
    print('checked message', flush=True)
    contract = Contract.objects.get(id=message['contractId'])
    now = timezone.now()
    contract.last_check = now
    next_check = now + datetime.timedelta(seconds=contract.check_interval)
    if next_check < contract.active_to:
        contract.next_check = next_check
    else:
        contract.state = 'EXPIRED'
        contract.next_check = None
    contract.save()
    print('checked ok', flush=True)

def repeat_check(message):
    print('repeat check message', flush=True)
    contract = Contract.objects.get(id=message['contractId'])
    check_one(contract)
    print('repeat check ok', flush=True)

def triggered(message):
    print('triggered message', flush=True)
    contract = Contract.objects.get(id=message['contractId'])
    contract.state = 'TRIGGERED'
    contract.last_check = timezone.now()
    contract.next_check = None
    contract.save()
    print('triggered ok', flush=True)


def unknown_handler(message):
    print('unknown message', message, flush=True)


methods_dict = {
    'payment': payment,
    'deployed': deployed,
    'killed': killed,
    'checked': checked,
    'repeatCheck': repeat_check,
    'triggered': triggered,
}

def callback(ch, method, properties, body):
    print('received', body, flush=True)
    try:
        message = json.loads(body.decode())
        if message.get('status', '') == 'COMMITTED':
            methods_dict.get(properties.type, unknown_handler)(message)
    except Exception as e:
        print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
    else:
#    finally:
        ch.basic_ack(delivery_tag = method.delivery_tag)


connection = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost',
        5672,
        'mywill',
        pika.PlainCredentials('java', 'java'),
))


"""
rabbitmqctl add_user java java
rabbitmqctl add_vhost mywill
rabbitmqctl set_permissions -p mywill java ".*" ".*" ".*"
"""

channel = connection.channel()
channel.queue_declare(queue=QUEUE, durable=True, auto_delete=False, exclusive=False)
channel.basic_consume(callback, queue=QUEUE)

channel.start_consuming()
