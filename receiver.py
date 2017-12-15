import pika
import os
import sys
import traceback
import json
import datetime
import sha3

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
    if contract.state in ('CREATED', 'WAITING_FOR_PAYMENT') and message['balance'] >= contract.cost:
        contract.get_details().deploy()
    print('payment ok', flush=True)

def deployed(message):
    print('deployed message received', flush=True)
    contract = Contract.objects.get(id=message['contractId'])
    contract.get_details().msg_deployed(message)
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
    contract.get_details().checked(message)
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
    contract.save()
    contract.get_details().triggered()
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
