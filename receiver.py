import pika
import os
import sys
import traceback
import json
import datetime
import sha3
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import F

from lastwill.contracts.models import Contract, EthContract, TxFail, NeedRequeue, AlreadyPostponed
from lastwill.settings import DEFAULT_FROM_EMAIL, MESSAGE_QUEUE
from lastwill.checker import check_one
from lastwill.profile.models import Profile
from exchange_API import to_wish


def payment(message):
    print('payment message', flush=True)
#    contract = Contract.objects.get(id=message['contractId'])
#    if contract.state in ('CREATED', 'WAITING_FOR_PAYMENT') and message['balance'] >= contract.cost:
#        contract.get_details().deploy()
    print('message["amount"]', message['amount'])
    value = message['amount'] if message['currency'] == 'WISH' else to_wish(
            message['currency'], message['amount']
    )
    print(value)
    Profile.objects.select_for_update().filter(user__id=message['userId']).update(balance=F('balance') + value)
    print('payment ok', flush=True)

def deployed(message):
    print('deployed message received', flush=True)
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.get_details().msg_deployed(message)
    print('deployed ok!', flush=True)

def killed(message):
    print('killed message', flush=True)
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.state = 'KILLED'
    contract.save()
    print('killed ok', flush=True)

def checked(message):
    print('checked message', flush=True)
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.get_details().checked(message)
    print('checked ok', flush=True)

def repeat_check(message):
    print('repeat check message', flush=True)
    contract = EthContract.objects.get(id=message['contractId']).contract
    check_one(contract)
    print('repeat check ok', flush=True)

def triggered(message):
    print('triggered message', flush=True)
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.state = 'TRIGGERED'
    contract.save()
    contract.get_details().triggered()
    print('triggered ok', flush=True)

def launch(message):
    print('launch message', flush=True)
    contract_details = Contract.objects.get(id=message['contractId']).get_details()
    contract_details.deploy()
    print('launch ok')

def unknown_handler(message):
    print('unknown message', message, flush=True)


def ownershipTransferred(message):
    print('ownershipTransferred message')
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.get_details().ownershipTransferred(message)
    print('ownershipTransferred ok')

def initialized(message):
    print('initialized message')
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.get_details().initialized(message)
    print('initialized ok')

methods_dict = {
    'payment': payment,
    'deployed': deployed,
    'killed': killed,
    'checked': checked,
    'repeatCheck': repeat_check,
    'triggered': triggered,
    'launch': launch,
    'initialized': initialized,
    'ownershipTransferred': ownershipTransferred,
}

def callback(ch, method, properties, body):
    print('received', body, properties, method, flush=True)
    try:
        message = json.loads(body.decode())
        if message.get('status', '') == 'COMMITTED':
            methods_dict.get(properties.type, unknown_handler)(message)
    except (TxFail, AlreadyPostponed):
        ch.basic_ack(delivery_tag = method.delivery_tag)
    except NeedRequeue:
        print('requeueing message', flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
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
channel.queue_declare(queue=MESSAGE_QUEUE, durable=True, auto_delete=False, exclusive=False)
channel.basic_consume(callback, queue=MESSAGE_QUEUE)

print('receiver started', flush=True)

channel.start_consuming()
