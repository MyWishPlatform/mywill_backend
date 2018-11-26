import time
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

from django.utils import timezone
from lastwill.payments.models import *
from lastwill.settings import FREEZE_THRESHOLD_EOS, FREEZE_THRESHOLD_ETH
from lastwill.contracts.models import Contract


def freeze_eth():
    pass


def freeze_eos():
    pass


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