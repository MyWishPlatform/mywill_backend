from ethereum import abi
import binascii
from django.utils import timezone
from lastwill.contracts.models import Contract
from lastwill.parint import *
from lastwill.settings import SIGNER

def check_one(contract):
    print('checking', contract.name)
    tr = abi.ContractTranslator(contract.abi)
    par_int = ParInt()
    nonce = int(par_int.parity_nextNonce(contract.owner_address), 16)
    print('nonce', nonce)
    response = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
            'source' : contract.owner_address,
            'data': binascii.hexlify(tr.encode_function_call('check', [])).decode(),
            'nonce': nonce,
            'dest': contract.address,
            'value': int(0.005 * 10 ** 18),
            'gaslimit': 300000,
    }).content.decode())
    print('response', response)
    signed_data = response['result']
    print('signed_data', signed_data)
    par_int.eth_sendRawTransaction('0x'+signed_data)
    print('check ok!')


def check_all():
    print('check_all method')
    for contract in Contract.objects.filter(next_check__lte=timezone.now(), contract_type__in=(0,1,4)):
       check_one(contract)

