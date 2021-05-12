from lastwill.consts import CONTRACT_PRICE_USDT
from lastwill.contracts.submodels.common import EthContract
from lastwill.contracts.submodels.ico import AbstractContractDetailsToken
from lastwill.contracts.submodels.common import *


class ContractDetailsXinFinToken(AbstractContractDetailsToken):
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='xinfin_token_details_token',
        on_delete=models.SET_NULL
    )

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='XINFIN_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        price = CONTRACT_PRICE_USDT['XINFIN_TOKEN']
        result = int(price * NET_DECIMALS['USDT']) # поменять децималы
        return result
