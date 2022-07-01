from lastwill.consts import CONTRACT_PRICE_USDT, NET_DECIMALS
from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.lostkey import AbstractContractDetailsLostKey


@contract_details('Binance Wallet contract (lost key)')
class ContractDetailsBinanceLostKey(AbstractContractDetailsLostKey):

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='BINANCE_SMART_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return CONTRACT_PRICE_USDT['BINANCE_LOSTKEY'] * NET_DECIMALS['USDT']
