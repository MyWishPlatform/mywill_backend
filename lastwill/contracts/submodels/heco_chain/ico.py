from lastwill.consts import NET_DECIMALS, CONTRACT_PRICE_USDT
from lastwill.contracts import models
from lastwill.contracts.decorators import contract_details
from lastwill.contracts.submodels.common import EthContract
from lastwill.contracts.submodels.ico import AbstractContractDetailsICO
from lastwill.deploy.models import Network


@contract_details('HecoChain MyWish ICO')
class ContractDetailsHecoChainICO(AbstractContractDetailsICO):
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='hecochain_ico_details_token',
        on_delete=models.SET_NULL
    )
    eth_contract_crowdsale = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='matic_ico_details_crowdsale',
        on_delete=models.SET_NULL
    )

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='HECOCHAIN_TESTNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(CONTRACT_PRICE_USDT['HECOCHAIN_ICO'] * NET_DECIMALS['HT'])
