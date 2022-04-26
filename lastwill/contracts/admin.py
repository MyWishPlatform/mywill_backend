from django.contrib import admin

from lastwill.contracts.models import (
    Contract, Heir, EthContract, TokenHolder, WhitelistAddress,
    NeoContract, SolanaContract, ContractDetailsNeoICO, ContractDetailsNeo,
    ContractDetailsToken, ContractDetailsICO,
    ContractDetailsAirdrop, AirdropAddress, TRONContract,
    ContractDetailsLastwill, ContractDetailsLostKey,
    ContractDetailsDelayedPayment, ContractDetailsInvestmentPool,
    InvestAddress, EOSTokenHolder, ContractDetailsEOSToken, EOSContract,
    ContractDetailsEOSAccount, ContractDetailsEOSICO, EOSAirdropAddress,
    ContractDetailsEOSAirdrop, ContractDetailsEOSTokenSA,
    ContractDetailsTRONToken, ContractDetailsGameAssets, ContractDetailsTRONAirdrop,
    ContractDetailsTRONLostkey, ContractDetailsLostKeyTokens,
    ContractDetailsWavesSTO, CurrencyStatisticsCache,
    ContractDetailsTokenProtector, ApprovedToken,
    ContractDetailsBinanceLostKeyTokens, ContractDetailsBinanceToken, ContractDetailsBinanceDelayedPayment,
    ContractDetailsBinanceLostKey, ContractDetailsBinanceLastwill, ContractDetailsBinanceInvestmentPool,
    ContractDetailsBinanceICO, ContractDetailsBinanceAirdrop,
    ContractDetailsMaticICO, ContractDetailsMaticToken, ContractDetailsMaticAirdrop,
    ContractDetailsXinFinToken, ContractDetailsHecoChainToken, ContractDetailsHecoChainICO,
    ContractDetailsMoonriverToken, ContractDetailsSolanaToken
)

# contracts
admin.site.register(CurrencyStatisticsCache)
admin.site.register(Contract)
admin.site.register(Heir)
admin.site.register(EthContract)
admin.site.register(TokenHolder)
admin.site.register(WhitelistAddress)
admin.site.register(NeoContract)
admin.site.register(SolanaContract)
admin.site.register(ContractDetailsNeoICO)
admin.site.register(ContractDetailsNeo)
admin.site.register(ContractDetailsToken)
admin.site.register(ContractDetailsICO)
admin.site.register(ContractDetailsAirdrop)
admin.site.register(AirdropAddress)
admin.site.register(TRONContract)
admin.site.register(ContractDetailsLastwill)
admin.site.register(ContractDetailsLostKey)
admin.site.register(ContractDetailsDelayedPayment)
admin.site.register(ContractDetailsInvestmentPool)
admin.site.register(InvestAddress)
admin.site.register(EOSTokenHolder)
admin.site.register(ContractDetailsEOSToken)
admin.site.register(EOSContract)
admin.site.register(ContractDetailsEOSAccount)
admin.site.register(ContractDetailsEOSICO)
admin.site.register(EOSAirdropAddress)
admin.site.register(ContractDetailsEOSAirdrop)
admin.site.register(ContractDetailsEOSTokenSA)
admin.site.register(ContractDetailsTRONToken)
admin.site.register(ContractDetailsGameAssets)
admin.site.register(ContractDetailsTRONAirdrop)
admin.site.register(ContractDetailsTRONLostkey)
admin.site.register(ContractDetailsLostKeyTokens)
admin.site.register(ContractDetailsWavesSTO)
admin.site.register(ContractDetailsTokenProtector)
admin.site.register(ApprovedToken)
admin.site.register(ContractDetailsBinanceLostKeyTokens)
admin.site.register(ContractDetailsBinanceToken)
admin.site.register(ContractDetailsBinanceDelayedPayment)
admin.site.register(ContractDetailsBinanceLostKey)
admin.site.register(ContractDetailsBinanceLastwill)
admin.site.register(ContractDetailsBinanceInvestmentPool)
admin.site.register(ContractDetailsBinanceICO)
admin.site.register(ContractDetailsBinanceAirdrop)
admin.site.register(ContractDetailsMaticICO)
admin.site.register(ContractDetailsMaticToken)
admin.site.register(ContractDetailsMaticAirdrop)
admin.site.register(ContractDetailsXinFinToken)
admin.site.register(ContractDetailsHecoChainToken)
admin.site.register(ContractDetailsHecoChainICO)
admin.site.register(ContractDetailsMoonriverToken)
admin.site.register(ContractDetailsSolanaToken)
