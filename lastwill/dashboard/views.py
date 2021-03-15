from django.contrib.auth.models import User
from datetime import datetime, time
from django.http import JsonResponse
from rest_framework.decorators import api_view
from lastwill.contracts.submodels.common import Contract
from lastwill.deploy.models import Network
from lastwill.settings import NETWORKS
from lastwill.dashboard.api import get_eos_balance, get_tron_balance, get_balance_via_w3, contracts_today_filter


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


@api_view()
def users_statistic_view():
    users = User.objects.all()
    now = datetime.now()
    midnight = datetime.combine(now.today(), time(0, 0))
    response = {
        'all': users.count(),
        'new': users.filter(date_joined__lte=midnight, date_joined__gte=now).count()
    }
    return JsonResponse(response)
