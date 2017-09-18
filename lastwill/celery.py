#from __future__ import absolute_import
import os
from ethereum import abi
from celery import Celery
from celery.schedules import crontab
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()
from django.utils import timezone
from .contracts.models import Contract
from lastwill.parint import *


app = Celery('lastwill')


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour=12, minute=0),
        check_task,
    )

app.autodiscover_tasks()

@app.task(bind=True)
def check_task(self):
    for contract in Contract.objects.filter(next_check__lte=timezone.now()):
        tr = abi.ContractTranslator(contract.abi)
        par_int = ParInt()
        nonce = int(par_int.parity_nextNonce(contract.owner.address), 16)
        signed_data = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
                'source' : contract.owner_address,
                'data': binascii.hexlify(tr.encode_function_call('check', [])).decode(),
                'nonce': nonce
        }).content.decode())['result']
        par_int.eth_sendRawTransaction('0x'+signed_data)
