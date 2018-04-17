from django.core.mail import send_mail

from lastwill.contracts.models import *
from lastwill.parint import *
from lastwill.settings import *


def move_funds(network):
    assert (network in ['RSK_MAINNET', 'RSK_TESTNET'])
    details = ContractDetailsLastwill.objects.filter(btc_duty__gt=0).order_by('btc_duty')
    if not details:
        return
    contract = details.first().contract
    par_int = ParInt(network)
    wl_address = NETWORKS[network]['whitelisted_address']
    balance = par_int.eth_getBalance(wl_address)
    gas_limit = 21000
    gas_price = 1
    if balance < contract.get_details().btc_duty + gas_limit * gas_price:
        send_mail(
            'RSK',
            'No RSK funds ' + network,
            DEFAULT_FROM_EMAIL,
            [EMAIL_FOR_POSTPONED_MESSAGE]
        )
        return
    nonce = int(par_int.eth_getTransactionCount(wl_address, "pending"), 16)

    response = json.loads(
        requests.post('http://{}/sign/'.format(SIGNER), json={
            'source': wl_address,
            'dest': contract.get_details().eth_contract.address,
            'nonce': nonce,
            'gaslimit': gas_limit,
            'gas_price': gas_price,
            'value': contract.get_details().btc_duty
        }).content.decode())
