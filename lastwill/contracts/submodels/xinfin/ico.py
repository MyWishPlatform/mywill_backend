from lastwill.contracts.submodels.ico import AbstractContractDetailsICO
from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS, CONTRACT_GAS_LIMIT, CONTRACT_PRICE_USDT


@contract_details('XinFin MyWish ICO')
class ContractDetailsXinFinICO(AbstractContractDetailsICO):
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='xinfin_ico_details_token',
        on_delete=models.SET_NULL
    )
    eth_contract_crowdsale = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='xinfin_ico_details_crowdsale',
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
        price = CONTRACT_PRICE_USDT['XINFIN_ICO']
        result = int(price * NET_DECIMALS['USDT'])
        if 'verification' in kwargs and kwargs['verification']:
            result = int(result + VERIVICATION_PRICE_USDT * NET_DECIMALS['USDT'])
        return result
