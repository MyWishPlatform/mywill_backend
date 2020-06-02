import time
import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django

django.setup()

from lastwill.settings import TRX_FREEZE_TIMEOUT, TRX_FREEZE_AMOUNT, NETWORKS
from lastwill.contracts.submodels.tron import instantiate_tronapi


if __name__ == '__main__':
    nets = [net for net in NETWORKS.keys() if 'TRON' in net]
    while True:
        time.sleep(TRX_FREEZE_TIMEOUT)
        for net in nets:
            tron = instantiate_tronapi(NETWORKS[net]['private_key'], net)
            unfreeze_tx = tron.trx.unfreeze('ENERGY')
            print(net, 'unfreeze_tx', unfreeze_tx, flush=True)
            time.sleep(10)
            freeze_tx = tron.trx.freeze(TRX_FREEZE_AMOUNT, 3, 'ENERGY')
            print(net, 'freeze_tx', freeze_tx, flush=True)
