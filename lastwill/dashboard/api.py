import requests
from datetime import datetime, time
from lastwill.consts import NET_DECIMALS
from lastwill.settings import NETWORKS
from web3 import Web3, HTTPProvider


def get_tron_balance(network):
    network_info = NETWORKS[network]
    url = f'{network_info["host"]}/v1/accounts/{network_info["address"]}'
    response = requests.get(url).json()
    balance = response['data'][0]['balance']
    return balance / NET_DECIMALS['TRON']


def get_eos_balance(network):
    network_info = NETWORKS[network]
    url = f'https://{network_info["host"]}/v1/chain/get_account'
    payload = {'account_name': network_info['address']}
    response = requests.post(url, json=payload).json()
    balance = response['core_liquid_balance']
    return balance


def get_balance_via_w3(network):
    w3 = Web3(HTTPProvider(NETWORKS[network]['node_url']))
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
