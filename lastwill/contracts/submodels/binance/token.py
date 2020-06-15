from lastwill.contracts.submodels.ico import AbstractContractDetailsToken
from lastwill.contracts.submodels.common import *


@contract_details('Binance Token contract')
class ContractDetailsBinanceToken(AbstractContractDetailsToken):
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='binance_token_details_token',
        on_delete=models.SET_NULL
    )
