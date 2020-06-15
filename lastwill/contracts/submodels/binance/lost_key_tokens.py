from lastwill.contracts.submodels.lostkey import AbstractContractDetailsLostKeyTokens
from lastwill.contracts.submodels.common import *


@contract_details('Binance Wallet contract (lost key)')
class ContractDetailsBinanceLostKeyTokens(AbstractContractDetailsLostKeyTokens):
    eth_contract = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='binance_lostkey_details',
        on_delete=models.SET_NULL
    )
