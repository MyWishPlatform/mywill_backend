import pika
import os
import sys
import traceback
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()
from django.core.mail import send_mail

from lastwill.contracts.models import Contract
from lastwill.settings import DEFAULT_FROM_EMAIL

QUEUE = 'notification'

def payment(message):
    print('payment message')
    contract = Contract.objects.get(id=message['contractId'])
    if contract.state in ('CREATED', 'WAITING_FOR_PAYMENT') and message['balance'] > contract.cost:
        contract.deploy()
    print('payment ok')

def deployed(message):
    print('deployed message received')
    contract = Contract.objects.get(id=message['contractId'])
    contract.address = message['address']
    contract.state = 'ACTIVE'
    contract.save()
    send_mail(
            'Contract deployed',
            'Contract deployed message',
            DEFAULT_FROM_EMAIL,
            [contract.user.email]
    )
    print('deployed ok!')

def killed(message):
    print('killed message')
    contract = Contract.objects.get(id=message['contractId'])
    contract.state = 'KILLED'
    contract.save()
    print('killed ok')

def unknown_handler(message):
    print('unknown message', message)

methods_dict = {
    'payment': payment,
    'deployed': deployed,
    'killed': killed,
}

def callback(ch, method, properties, body):
    print('received', body)
    try:
        message = json.loads(body.decode())
        if message.get('status', '') == 'COMMITTED':
            methods_dict.get(properties.type, unknown_handler)(message)
    except Exception as e:
        print('\n'.join(traceback.format_exception(*sys.exc_info())))
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
