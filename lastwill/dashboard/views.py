from django.contrib.auth.models import User
from datetime import datetime, time
from django.http import JsonResponse
from rest_framework.decorators import api_view
from lastwill.contracts.submodels.common import Contract
from lastwill.rates.api import rate
from lastwill.settings import NETWORKS, DASHBOARD_NETWORKS
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


def generate_contracts_statistic(network, types):
    total = Contract.objects.filter(network__name=network)
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
    users = User.objects.all()
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
