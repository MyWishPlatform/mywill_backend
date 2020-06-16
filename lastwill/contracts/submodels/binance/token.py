from lastwill.contracts.submodels.ico import AbstractContractDetailsToken
from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS, CONTRACT_GAS_LIMIT, CONTRACT_PRICE_USDT


@contract_details('Binance Token contract')
class ContractDetailsBinanceToken(AbstractContractDetailsToken):
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='binance_token_details_token',
        on_delete=models.SET_NULL
    )

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='BINANCE_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        price = CONTRACT_PRICE_USDT['BINANCE_TOKEN']
        result = int(price * NET_DECIMALS['USDT'])
        # if 'authio' in kwargs and kwargs['authio']:
        #     result = int(price + CONTRACT_PRICE_USDT['ETH_TOKEN_AUTHIO'] * NET_DECIMALS['USDT'])
        return result
