from lastwill.consts import (AUTHIO_PRICE_USDT, CONTRACT_GAS_LIMIT, CONTRACT_PRICE_USDT, NET_DECIMALS,
                             VERIFICATION_PRICE_USDT, WHITELABEL_PRICE_USDT)
from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.ico import AbstractContractDetailsToken


@contract_details('Matic Token contract')
class ContractDetailsMaticToken(AbstractContractDetailsToken):
    eth_contract_token = models.ForeignKey(EthContract,
                                           null=True,
                                           default=None,
                                           related_name='matic_token_details_token',
                                           on_delete=models.SET_NULL)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='MATIC_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        price = CONTRACT_PRICE_USDT['MATIC_TOKEN']
        if 'authio' in kwargs and kwargs['authio']:
            price += AUTHIO_PRICE_USDT
        if 'verification' in kwargs and kwargs['verification']:
            price += VERIFICATION_PRICE_USDT
        if 'white_label' in kwargs and kwargs['white_label']:
            price += WHITELABEL_PRICE_USDT
        return price * NET_DECIMALS['USDT']
