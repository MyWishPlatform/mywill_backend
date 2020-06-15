from lastwill.contracts.submodels.ico import AbstractContractDetailsICO
from lastwill.contracts.submodels.common import *


@contract_details('Binance MyWish ICO')
class ContractDetailsBinanceICO(AbstractContractDetailsICO):
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='binance_ico_details_token',
        on_delete=models.SET_NULL
    )
    eth_contract_crowdsale = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='binance_ico_details_crowdsale',
        on_delete=models.SET_NULL
    )
