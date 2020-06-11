import time
import os
import datetime


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django

django.setup()

from lastwill.settings import TRX_FREEZE_TIMEOUT, TRX_FREEZE_AMOUNT, NETWORKS
from lastwill.contracts.submodels.tron import instantiate_tronapi


if __name__ == '__main__':
    while True:
        nets = [net for net in NETWORKS.keys() if 'TRON' in net]
        print('nets', nets, '\n', flush=True)
        time.sleep(TRX_FREEZE_TIMEOUT)
        for net in nets:
            tron = instantiate_tronapi(NETWORKS[net]['private_key'], net)
            unfreeze_tx = tron.trx.unfreeze_balance('ENERGY')
            print(net, 'unfreeze_tx at', datetime.datetime.now(), '\n', unfreeze_tx, '\n', flush=True)
            time.sleep(10)
            freeze_tx = tron.trx.freeze_balance(TRX_FREEZE_AMOUNT, 3, 'ENERGY')
            print(net, 'freeze_tx at', datetime.datetime.now(), '\n', freeze_tx, '\n', flush=True)
