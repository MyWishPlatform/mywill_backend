from lastwill.consts import (CONTRACT_GAS_LIMIT, CONTRACT_PRICE_USDT, NET_DECIMALS)
from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.lastwill import \
    AbstractContractDetailsLastwill


@contract_details('Binance Will contract')
class ContractDetailsBinanceLastwill(AbstractContractDetailsLastwill):

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='BINANCE_SMART_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return CONTRACT_PRICE_USDT['BINANCE_LASTWILL'] * NET_DECIMALS['USDT']

    def get_arguments(self, *args, **kwargs):
        return [
            self.user_address,
            [h.address for h in self.contract.heir_set.all()],
            [h.percentage for h in self.contract.heir_set.all()],
            self.check_interval,
            False,
        ]
