import sys, traceback
from time import sleep

from django.db.models import Q
from django.core.mail import send_mail

from lastwill.deploy.models import DeployAddress
from lastwill.settings import DEFAULT_FROM_EMAIL, EMAIL_FOR_POSTPONED_MESSAGE
from lastwill.settings import test_logger, NETWORKS
from email_messages import *


contract_details_types = []


def contract_details(name):
    def w(c):
        contract_details_types.append({
                'name': name,
                'model': c,
        })
        return c
    return w

class NeedRequeue(Exception):
    pass


class TxFail(Exception):
    pass


class AlreadyPostponed(Exception):
    pass


def check_transaction(f):
    def wrapper(*args, **kwargs):
        if not args[1].get('success', True):
            print('message rejected because transaction failed', flush=True)
            test_logger.error('transaction failed')
            raise TxFail()
        else:
            return f(*args, **kwargs)
    return wrapper


def postponable(f):
    def wrapper(*args, **kwargs):
        contract = args[0].contract
        if contract.state == 'POSTPONED':
            test_logger.error('contract postponed')
            print('message rejected because contract postponed', flush=True)
            send_mail(
                postponed_subject,
                postponed_message.format(
                    contract_id=contract.id
                ),
                DEFAULT_FROM_EMAIL,
                [EMAIL_FOR_POSTPONED_MESSAGE]
            )

            raise AlreadyPostponed
        try:
            return f(*args, **kwargs)
        except Exception as e:
            contract.state = 'POSTPONED'
            contract.save()
            send_mail(
                postponed_subject,
                postponed_message.format(
                    contract_id=contract.id
                ),
                DEFAULT_FROM_EMAIL,
                [EMAIL_FOR_POSTPONED_MESSAGE]
            )
            print('contract postponed due to exception', flush=True)
            test_logger.error('contract postponed due to exception')
            address = NETWORKS[contract.network.name]['address']
            DeployAddress.objects.select_for_update().filter(
                network__name=contract.network.name,
                address=address, locked_by=contract.id
            ).update(locked_by=None)
            print('queue unlocked due to exception', flush=True)
            test_logger.error('queue unlocked due to exception')
            raise
    return wrapper


def blocking(f):
    def wrapper(*args, **kwargs):
        network_name = args[0].contract.network.name
        address = NETWORKS[args[0].contract.network.name]['address']
        if not DeployAddress.objects.select_for_update().filter(
                Q(network__name=network_name) & Q(address=address) & (Q(locked_by__isnull=True) | Q(locked_by=args[0].contract.id))
        ).update(locked_by=args[0].contract.id):
            print('address locked. sleeping 5 and requeueing the message', flush=True)
            sleep(5)
            raise NeedRequeue()
        return f(*args, **kwargs)
    return wrapper


def logging(f):
    def wrapper(*args, **kwargs):
        info1 = ','.join([str(ar) for ar in args])
        info2 = ','.join([str(ar) for ar in kwargs])
        str_info = 'CONTRACT LOGGING ' + str(f.__qualname__) + info1 + info2
        test_logger.info(str_info)
        try:
            return f(*args, **kwargs)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            trace_back = ' '. join(
                traceback.format_exception(exc_type, exc_value,exc_traceback)
            )
            test_logger.error('CONTRACT LOGGING ' + str(f.__qualname__) + str(exc_value) + trace_back)
            raise
    return wrapper
