import time
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

from django.utils import timezone
from lastwill.payments.models import *
from lastwill.settings import FREEZE_THRESHOLD_EOS, FREEZE_THRESHOLD_ETH, NETWORKS
from lastwill.contracts.models import Contract, implement_cleos_command, unlock_eos_account


def freeze_eth():
    pass


def freeze_eos():
    # wallet_name = NETWORKS['EOS_MAINNET']['wallet']
    # password = NETWORKS['EOS_MAINNET']['eos_password']
    # unlock_eos_account(wallet_name, password)
    public_key = ''
    command_list = [
        'cleos', 'push', 'action', 'eosio.token', 'transfer',
        '[ "{address_from}", "{address_to}", "{amount} EOSISH", "m" ]'.format(
            address_from='',
            address_to='',
            amount=FREEZE_THRESHOLD_EOS
        ),
        '-p', public_key
    ]
    implement_cleos_command(command_list)


def check_payments():
    freeze_balance = FreezeBalance.objects.all().first()
    if freeze_balance.eos > FREEZE_THRESHOLD_EOS:
        freeze_eos()
    if freeze_balance.eth > FREEZE_THRESHOLD_ETH:
        freeze_eth()


if __name__ == '__main__':
    while 1:
        check_payments()
        time.sleep(60 * 5)