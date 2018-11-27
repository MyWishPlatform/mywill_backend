import time
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

from django.utils import timezone
from lastwill.payments.models import *
from lastwill.settings import FREEZE_THRESHOLD_EOSISH, FREEZE_THRESHOLD_WISH, NETWORKS
from lastwill.contracts.models import Contract, implement_cleos_command, unlock_eos_account


def freeze_wish():
    pass


def freeze_eosish():
    # wallet_name = NETWORKS['EOS_MAINNET']['wallet']
    # password = NETWORKS['EOS_MAINNET']['eos_password']
    # unlock_eos_account(wallet_name, password)
    public_key = ''
    command_list = [
        'cleos', 'push', 'action', 'eosio.token', 'transfer',
        '[ "{address_from}", "{address_to}", "{amount} EOSISH", "m" ]'.format(
            address_from='',
            address_to='',
            amount=FREEZE_THRESHOLD_EOSISH
        ),
        '-p', public_key
    ]
    implement_cleos_command(command_list)


def check_payments():
    freeze_balance = FreezeBalance.objects.all().first()
    if freeze_balance.eosish > FREEZE_THRESHOLD_EOSISH:
        freeze_eosish()
    if freeze_balance.wish > FREEZE_THRESHOLD_WISH:
        freeze_wish()


if __name__ == '__main__':
    while 1:
        check_payments()
        time.sleep(60 * 5)