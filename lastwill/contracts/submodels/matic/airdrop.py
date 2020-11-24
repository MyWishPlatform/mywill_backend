from lastwill.contracts.submodels.airdrop import AbstractContractDetailsAirdrop
from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS, CONTRACT_GAS_LIMIT, CONTRACT_PRICE_USDT


@contract_details('Matic Airdrop')
class ContractDetailsMaticAirdrop(AbstractContractDetailsAirdrop):

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return CONTRACT_PRICE_USDT['MATIC_AIRDROP'] * NET_DECIMALS['USDT']

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='MATIC_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost
