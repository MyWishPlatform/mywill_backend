import requests
from datetime import datetime, time
from lastwill.consts import NET_DECIMALS
from lastwill.parint import EthereumProvider
from lastwill.settings import NETWORKS
from web3 import Web3, HTTPProvider


def get_tron_balance(network):
    url = f'{NETWORKS[network]["host"]}/v1/accounts/{NETWORKS[network]["address"]}'
    response = requests.get(url)
    if response.status_code == 200:
        balance = response.json()['data'][0]['balance']
        return balance / NET_DECIMALS['TRON']
    return None


def get_eos_balance(network):
    url = f'https://{NETWORKS[network]["host"]}/v1/chain/get_account'
    payload = {'account_name': NETWORKS[network]['address']}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        balance = data['core_liquid_balance']
        return float(balance.split(' ')[0])  # API returns "123.45 EOS"
    return None


def get_balance_via_w3(network):
    w3 = Web3(HTTPProvider(NETWORKS[network]['node_url']))
    try:
        checksum_address = w3.toChecksumAddress(NETWORKS[network]['address'])
        raw_balance = w3.eth.getBalance(checksum_address)
        return raw_balance / NET_DECIMALS['ETH']
    except Exception:
        return None


def get_eth_balance(network):
    provider = EthereumProvider().get_provider(network=network)
    w3 = Web3(HTTPProvider(provider.url))
    try:
        checksum_address = w3.toChecksumAddress(NETWORKS[network]['address'])
        raw_balance = w3.eth.getBalance(checksum_address)
        return raw_balance / NET_DECIMALS['ETH']
    except Exception:
        return None



def contracts_today_filter(contracts):
    now = datetime.now()
    midnight = datetime.combine(now.today(), time(0, 0))
    return contracts.filter(created_date__gte=midnight, created_date__lte=now)
