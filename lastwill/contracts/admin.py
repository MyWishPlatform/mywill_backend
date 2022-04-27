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
@admin.register(CurrencyStatisticsCache)
class CurrencyStatisticsCacheAdmin(admin.ModelAdmin):
    list_display = '__str__', 'wish_usd_percent_change_24h', 'btc_percent_change_24h', \
                   'eth_percent_change_24h', 'eos_percent_change_24h', 'usd_percent_change_24h'


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = '__str__', 'state', 'created_date', 'last_check', 'active_to'


@admin.register(Heir)
class HeirAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'percentage'


@admin.register(EthContract)
class EthContractAdmin(admin.ModelAdmin):
    model = EthContract
    list_display = '__str__', 'get_original_contract_address', 'address'

    def get_original_contract_address(self, obj):
        return obj.original_contract.address


@admin.register(TokenHolder)
class TokenHolderAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'amount', 'freeze_date'


@admin.register(WhitelistAddress)
class WhitelistAddressAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'active'


@admin.register(NeoContract)
class NeoContractAdmin(admin.ModelAdmin):
    model = NeoContract
    list_display = '__str__', 'get_original_contract_address', 'address'

    def get_original_contract_address(self, obj):
        return obj.original_contract.address


@admin.register(SolanaContract)
class SolanaContractAdmin(admin.ModelAdmin):
    model = SolanaContract
    list_display = '__str__', 'get_original_contract_address', 'address'

    def get_original_contract_address(self, obj):
        return obj.original_contract.address


admin.site.register(ContractDetailsNeoICO)
admin.site.register(ContractDetailsNeo)
admin.site.register(ContractDetailsToken)
admin.site.register(ContractDetailsICO)
admin.site.register(ContractDetailsAirdrop)
admin.site.register(AirdropAddress)


@admin.register(TRONContract)
class TRONContractAdmin(admin.ModelAdmin):
    model = TRONContract
    list_display = '__str__', 'get_original_contract_address', 'address'

    def get_original_contract_address(self, obj):
        return obj.original_contract.address


admin.site.register(ContractDetailsLastwill)
admin.site.register(ContractDetailsLostKey)
admin.site.register(ContractDetailsDelayedPayment)
admin.site.register(ContractDetailsInvestmentPool)
admin.site.register(InvestAddress)
admin.site.register(EOSTokenHolder)
admin.site.register(ContractDetailsEOSToken)


@admin.register(EOSContract)
class EOSContractAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address'


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
