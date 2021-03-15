import requests
from datetime import datetime, time
from django.http import JsonResponse
from rest_framework.decorators import api_view
from lastwill.consts import NET_DECIMALS
from lastwill.contracts.submodels.common import Contract
from lastwill.deploy.models import Network
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


def contracts_today_filter(contracts):
    now = datetime.now()
    midnight = datetime.combine(now.today(), time(0, 0))
    return contracts.filter(created_date__gte=midnight, created_date__lte=now)


@api_view()
def contracts_statistic_by_ids_view(request):
    contracts = Contract.objects.all()
    contract_types = Contract.get_all_details_model()
    result = {}
    for i, contract_type in enumerate(contract_types):
        contracts = contracts.filter(contract_type=contract_type)
        result[i] = {
            'all': contracts.count(),
            'new': contracts_today_filter(contracts).count()
        }
    return JsonResponse(result)


@api_view()
def contracts_common_statistic_view(request):
    networks = Network.objects.all()
    response = {}
    for network in networks:
        contracts = Contract.objects.filter(network=network)
        created = contracts.filter(state='CREATED')
        deployed = contracts.filter(state__in=('ACTIVE', 'WAITING', 'WAITING_ACTIVATION'))
        postponed = contracts.filter(state='POSTPONED')
        in_process = contracts.filter(state='WAITING_FOR_DEPLOYMENT')

        response[network.name] = {
            'total': {
                'all': contracts.count(),
                'new': contracts_today_filter(contracts).count(),
            },
            'created': {
                'all': created.count(),
                'new': contracts_today_filter(created).count(),
            },
            'deployed': {
                'all': deployed.count(),
                'new': contracts_today_filter(deployed).count(),
            },
            'postponed': {
                'all': postponed.count(),
                'new': contracts_today_filter(deployed).count(),
            },
            'in_process': {
                'all': in_process.count(),
                'new': contracts_today_filter(in_process).count(),
            },
        }

    return JsonResponse(response)
