import requests
import json
import binascii
from ethereum import abi

from lastwill.contracts.submodels.common import Contract, sign_transaction
from lastwill.contracts.decorators import take_off_blocking
from lastwill.settings import NETWORKS


class InfuraConnectExc(Exception):
    def __init__(self, *args):
        self.value = 'can not connect to infura'

    def __str__(self):
        return self.value


class InfuraErrorExc(Exception):
    pass


class InfuraInt:
    def __init__(self, network=None):
        if network == 'TESTNET':
            self.url = 'https://ropsten.infura.io/v3/c139df87547b41c9b3b3a1c148913286'
        if network == 'MAINNET':
            self.url = 'https://mainnet.infura.io/v3/1bb65ebf85d84cf6bd46808752e444a0'
        print('parity interface', self.url, flush=True)

    def __getattr__(self, method):
        def f(*args):
            arguments = {
                    'method': method,
                    'params': args,
                    'id': 1,
                    'jsonrpc': '2.0',
            }
            try:
                temp = requests.post(
                        self.url,
                        json=arguments,
                        headers={'Content-Type': 'application/json'}
                )
            except requests.exceptions.ConnectionError as e:
                raise InfuraConnectExc()
            print('raw response', temp.content, flush=True)
            result = json.loads(temp.content.decode())
            if result.get('error'):
                raise InfuraErrorExc(result['error']['message'])
            return result['result']
        return f


def deploy_with_infura(contract_id, eth_contract_attr_name, network):
    c = Contract.objects.get(id=contract_id)
    det = c.get_details()
    if det.contract.state not in ('CREATED', 'WAITING_FOR_DEPLOYMENT'):
        print('launch message ignored because already deployed', flush=True)
        take_off_blocking(c.network.name)
        return
    det.compile()
    eth_contract = getattr(det, eth_contract_attr_name)
    tr = abi.ContractTranslator(eth_contract.abi)
    arguments = det.get_arguments(eth_contract_attr_name)
    print('arguments', arguments, flush=True)
    eth_contract.constructor_arguments = binascii.hexlify(
        tr.encode_constructor_arguments(arguments)
    ).decode() if arguments else ''
    infura_int = InfuraInt(network=network)
    address = NETWORKS[det.contract.network.name]['address']
    nonce = int(infura_int.eth_getTransactionCount(address, "pending"), 16)
    print('nonce', nonce, flush=True)
    data = eth_contract.bytecode + (binascii.hexlify(
        tr.encode_constructor_arguments(arguments)
    ).decode() if arguments else '')
    gas_price = 41 * 10 ** 9
    signed_data = sign_transaction(
        address, nonce, det.get_gaslimit(),
        det.contract.network.name, value=det.get_value(),
        contract_data=data, gas_price=gas_price
    )
    print('fields of transaction', flush=True)
    print('source', address, flush=True)
    print('gas limit', det.get_gaslimit(), flush=True)
    print('value', det.get_value(), flush=True)
    print('network', det.contract.network.name, flush=True)
    eth_contract.tx_hash = infura_int.eth_sendRawTransaction(
        '0x' + signed_data
    )
    eth_contract.save()
    print('transaction sent', flush=True)
    det.contract.state = 'WAITING_FOR_DEPLOYMENT'
    det.contract.save()
