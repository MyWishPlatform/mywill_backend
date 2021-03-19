import json
from os import path
from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework.decorators import api_view
from lastwill.contracts.submodels.common import Contract
from lastwill.rates.api import rate
from lastwill.settings import DASHBOARD_NETWORKS, BASE_DIR
from lastwill.dashboard.api import *


@api_view()
def deploy_accounts_balances_view(request):
    response = {}
    for network, info in DASHBOARD_NETWORKS.items():
        if network in ('ETHEREUM', 'BINANCE_SMART_CHAIN', 'MATIC'):
            response[network] = {
                'mainnet': get_balance_via_w3(info['original_name']['mainnet']),
                'testnet': get_balance_via_w3(info['original_name']['testnet']),
            }
        elif network == 'ETHEREUM':
            response[network] = {
                'mainnet': get_eth_balance(info['original_name']['mainnet']),
                'testnet': get_eth_balance(info['original_name']['testnet']),
            }
        elif network == 'TRON':
            response[network] = {
                'mainnet': get_tron_balance(info['original_name']['mainnet']),
                'testnet': get_tron_balance(info['original_name']['testnet']),
            }
        elif network == 'EOSIO':
            response[network] = {
                'mainnet': get_eos_balance(info['original_name']['mainnet']),
                'testnet': get_eos_balance(info['original_name']['testnet']),
            }
    return JsonResponse(response)


def get_users():
    try:
        filename = path.join(BASE_DIR, 'lastwill/contracts/test_addresses.json')
        test_emails = json.load(open(filename))['addresses']
    except(FileNotFoundError, IOError):
        test_emails = []

    users = User.objects.all().exclude(
        email__in=test_emails).exclude(
        email='', password='', last_name='', first_name='').exclude(
        email__startswith='testermc')

    return users


def generate_contracts_statistic(network, types):
    total = Contract.objects.filter(network__name=network, user__in=get_users())
    created = total.filter(state='CREATED')
    deployed = total.filter(state__in=('ACTIVE', 'WAITING', 'WAITING_ACTIVATION'))
    postponed = total.filter(state='POSTPONED')
    in_process = total.filter(state='WAITING_FOR_DEPLOYMENT')

    contracts_by_types = {}
    for name, type in types.items():
        contracts = total.filter(contract_type=type)
        contracts_by_types[name] = {
            'all': contracts.count(),
            'new': contracts_today_filter(contracts).count()
        }

    result = {
        'total': {
            'all': total.count(),
            'new': contracts_today_filter(total).count(),
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
            'new': contracts_today_filter(postponed).count(),
        },
        'in_process': {
            'all': in_process.count(),
            'new': contracts_today_filter(in_process).count(),
        },
        'types': contracts_by_types
    }
    return result


@api_view()
def contracts_statistic_view(request):
    response = {}
    for network, info in DASHBOARD_NETWORKS.items():
        response[network] = {
            'mainnet': generate_contracts_statistic(info['original_name']['mainnet'], info['contracts']),
            'testnet': generate_contracts_statistic(info['original_name']['testnet'], info['contracts']),
        }

    return JsonResponse(response)


@api_view()
def users_statistic_view(request):
    users = get_users()
    now = datetime.now()
    midnight = datetime.combine(now.today(), time(0, 0))
    response = {
        'all': users.count(),
        'new': users.filter(date_joined__lte=midnight, date_joined__gte=now).count()
    }
    return JsonResponse(response)


@api_view()
def advanced_rate_view(request):
    fsyms = request.query_params['fsyms'].split(',')
    tsyms = request.query_params['tsyms'].split(',')
    response = {}
    for fsym in fsyms:
        rates = {}
        for tsym in tsyms:
            rate_obj = rate(fsym, tsym)
            rates[tsym] = {
                'rate': rate_obj.value,
                'is_24h_up': rate_obj.is_up_24h,
            }
        response[fsym] = rates
    return JsonResponse(response)
