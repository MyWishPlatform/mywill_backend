from lastwill.consts import (CONTRACT_GAS_LIMIT, CONTRACT_PRICE_USDT, NET_DECIMALS)
from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.investment_pool import \
    AbstractContractDetailsInvestmentPool


@contract_details('Binance Investment Pool')
class ContractDetailsBinanceInvestmentPool(AbstractContractDetailsInvestmentPool):

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return CONTRACT_PRICE_USDT['BINANCE_INVPOOL'] * NET_DECIMALS['USDT']

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='BINANCE_SMART_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost
