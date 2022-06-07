from lastwill.consts import CONTRACT_PRICE_USDT, NET_DECIMALS
from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.lostkey import \
    AbstractContractDetailsLostKeyTokens


@contract_details('Binance Wallet contract (lost key)')
class ContractDetailsBinanceLostKeyTokens(AbstractContractDetailsLostKeyTokens):
    eth_contract = models.ForeignKey(EthContract,
                                     null=True,
                                     default=None,
                                     related_name='binance_lostkey_details',
                                     on_delete=models.SET_NULL)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='BINANCE_SMART_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(CONTRACT_PRICE_USDT['BINANCE_LOSTKEY_TOKENS'] * NET_DECIMALS['USDT'])
