import requests
from datetime import datetime, time
from lastwill.consts import NET_DECIMALS
from lastwill.parint import EthereumProvider
from lastwill.settings import NETWORKS
from web3 import Web3, HTTPProvider
from lastwill.contracts.models import Contract
from lastwill.deploy.models import Network
from collections import defaultdict
from lastwill.consts import AVAILABLE_CONTRACT_TYPES


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


def contracts_today_filter(contracts, field_name):
    now = datetime.now()
    midnight = datetime.combine(now.today(), time(0, 0))
    return contracts.filter(**{f'{field_name}__gte': midnight, f'{field_name}__lte': now})


def deployed_contracts_statistic(from_date, to_date, is_testnet=True):
    if is_testnet:
        networks = Network.objects.exclude(name__endswith='MAINNET')
    else:
        networks = Network.objects.filter(name__endswith='MAINNET')

    for network in networks:
        results = {}
        results = defaultdict(lambda: {'amount': 0,
                                       'with_verification': 0,
                                       'with_authio': 0,
                                       'cost': 0}, results)
        contracts = Contract.objects.filter(network=network,
                                            deployed_at__gte=from_date,
                                            deployed_at__lte=to_date)

        contract_types = AVAILABLE_CONTRACT_TYPES.get(network.id, [])
        for contract in contracts:
            type_result = results[contract.contract_type]
            type_result['amount'] += 1
            type_result['cost'] += contract.cost
            if getattr(contract.get_details(), 'verification', None):
                type_result['with_verification'] += 1
            if getattr(contract.get_details(), 'authio', None):
                type_result['with_authio'] += 1

        print(network.name)
        for type_num, type_result in results.items():
            for contract_type_dict in contract_types:
                if contract_type_dict['contract_type'] == type_num:
                    print(contract_type_dict['contract_name'], type_result)
                    break
            else:
                print(type_num, type_result)
