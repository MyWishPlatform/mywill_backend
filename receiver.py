import pika
import os
import sys
import traceback
import json
import datetime
import sha3
import requests
import sys
from pika.exceptions import ConnectionClosed

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import F
from django.core.exceptions import ObjectDoesNotExist

from lastwill.contracts.models import Contract, EthContract, TxFail, NeedRequeue, AlreadyPostponed
from lastwill.settings import DEFAULT_FROM_EMAIL, NETWORKS
from checker import check_one
from lastwill.profile.models import Profile
from lastwill.deploy.models import DeployAddress
from lastwill.payments.functions import create_payment
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
    # Profile.objects.select_for_update().filter(user__id=message['userId']).update(balance=F('balance') + value)
    print('payment ok', flush=True)
    create_payment(message['userId'], value, message['transactionHash'], message['currency'], message['amount'])

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
    network = contract.network
    DeployAddress.objects.filter(network=network, locked_by=contract.id).update(locked_by=None)
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
    contract.get_details().triggered(message)
    print('triggered ok', flush=True)

def launch(message):
    print('launch message', flush=True)
    try:
        contract_details = Contract.objects.get(id=message['contractId']).get_details()
        contract_details.deploy()
    except ObjectDoesNotExist:
        # only when contract removed manually
        print('no contract, ignoging')
        return
    contract_details.refresh_from_db()
    print('launch ok')

def unknown_handler(message):
    print('unknown message', message, flush=True)


def ownershipTransferred(message):
    print('ownershipTransferred message')
#    contract = EthContract.objects.get(id=message['contractId']).contract
#    contract = EthContract.objects.get(id=message['contractId']).ico_details_token.all().order_by('-id').first().contract
    contract = EthContract.objects.get(id=message['crowdsaleId']).contract
    contract.get_details().ownershipTransferred(message)
    print('ownershipTransferred ok')

def initialized(message):
    print('initialized message')
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.get_details().initialized(message)
    print('initialized ok')

def finish(message):
    print('finish message')
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.get_details().finalized(message)
    print('finish ok')

def finalized(message):
    print('finalized message')
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.get_details().finalized(message)
    print('finalized ok')

def transactionCompleted(message):
    print('transactionCompleted')
    if message['transactionStatus']:
        print('success, ignoring')
        return
    try:
        contract = EthContract.objects.get(tx_hash=message['transactionHash']).contract
        '''
        contract = Contract.objects.get(id=message['lockedBy'])
        assert((contract.contract_type not in (4,5) and message['transactionHash'] == contract.get_details().eth_contract.tx_hash) or
                (contract.contract_type == 4 and message['transactionHash'] in (contract.get_details().eth_contract_token.tx_hash, contract.get_details().eth_contract_crowdsale.tx_hash)) or 
                (contract.contract_type == 5 and message['transactionHash'] == contract.get_details().eth_contract_token.tx_hash)
        )
        '''
        contract.get_details().tx_failed(message)
    except Exception as e:
        print(e)
        print('not found, returning')
        return
    print('transactionCompleted ok')


def cancel(message):
    print('cancel message')
    contract = Contract.objects.get(id=message['contractId'])
    contract.get_details().cancel(message)
    print('cancel ok')


def confirm_alive(message):
    print('confirm_alive message')
    contract = Contract.objects.get(id=message['contractId'])
    contract.get_details().i_am_alive(message)
    print('confirm_alive ok')


def contractPayment(message):
    print('contract Payment message')
    contract = EthContract.objects.get(id=message['contractId']).contract
    contract.get_details().contractPayment(message)
    print('contract Payment ok')


def notified(message):
    print('notified message')
    contract = EthContract.objects.get(id=message['contractId']).contract
    details = contract.get_details()
    details.last_reset = timezone.now()
    details.save()
    print('notified ok')

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
    'finalized': finalized,
    'finish': finish,
    'transactionCompleted': transactionCompleted,
    'confirm_alive': confirm_alive,
    'cancel': cancel,
    'contractPayment': contractPayment,
    'notified': notified,
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




"""
rabbitmqctl add_user java java
rabbitmqctl add_vhost mywill
rabbitmqctl set_permissions -p mywill java ".*" ".*" ".*"
"""

connection = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost',
        5672,
        'mywill',
        pika.PlainCredentials('java', 'java'),
        heartbeat_interval = 0,
))

network = sys.argv[1]

channel = connection.channel()
channel.queue_declare(queue=NETWORKS[network]['queue'], durable=True, auto_delete=False, exclusive=False)
channel.basic_consume(callback, queue=NETWORKS[network]['queue'])



print('receiver started', flush=True)
print('listening', network, flush=True)

channel.start_consuming()

