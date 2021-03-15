import datetime
import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view
from lastwill.consts import NET_DECIMALS
from lastwill.contracts.submodels.common import Contract
from lastwill.settings import TRON_BALANCE_API_URL, EOS_ACCOUNT_API_URL, NETWORKS, BASE_DIR
from web3 import Web3, HTTPProvider


def get_tron_balance(address, testnet=False):
    url = TRON_BALANCE_API_URL['testnet' if testnet else 'mainnet'].format(address=address)
    response = requests.get(url).json()
    balance = response['data'][0]['balance']
    return balance / NET_DECIMALS['TRON']


def get_eos_balance(account, testnet=False):
    url = EOS_ACCOUNT_API_URL['testnet' if testnet else 'mainnet']
    payload = {'account_name': account}
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


@api_view()
def deploy_accounts_balances_view(request):
    response = {
        'Ethereum': {
            'mainnet': get_balance_via_w3('ETHEREUM_MAINNET'),
            'testnet': get_balance_via_w3('ETHEREUM_ROPSTEN'),
        },
        'Binance-Smart-Chain': {
            'mainnet': get_balance_via_w3('BINANCE_SMART_MAINNET'),
            'testnet': get_balance_via_w3('BINANCE_SMART_TESTNET'),
        },
        'Matic': {
            'mainnet': get_balance_via_w3('MATIC_MAINNET'),
            'testnet': get_balance_via_w3('MATIC_TESTNET'),
        },
        'Tron': {
            'mainnet': get_tron_balance(NETWORKS['TRON_MAINNET']['address']),
            'testnet': get_tron_balance(NETWORKS['TRON_TESTNET']['address'], testnet=True),
        },
        'Eosio': {
            'mainnet': get_eos_balance(NETWORKS['EOS_MAINNET']['address']),
            'testnet': get_eos_balance(NETWORKS['EOS_TESTNET']['address'], testnet=True),
        }
    }
    return JsonResponse(response)


@api_view()
def contract_statistic_by_ids_view(request):
    contracts = Contract.objects.all()
    contract_details_types = Contract.get_all_details_model()

    now = datetime.datetime.now()
    day = datetime.datetime.combine(
        datetime.datetime.now().today(),
        datetime.time(0, 0)
    )

    result = {}

    for i, contract_type in enumerate(contract_details_types):
        all_contracts = contracts.filter(contract_type=contract_type)
        info = {
            'all': all_contracts.count(),
            'new': all_contracts.filter(created_date__lte=now, created_date__gte=day).count()
        }
        result[i] = info

    return JsonResponse(result)
