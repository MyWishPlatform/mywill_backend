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
    ContractDetailsMoonriverToken, ContractDetailsSolanaToken, ProtectorChecker
)


# contracts
@admin.register(CurrencyStatisticsCache)
class CurrencyStatisticsCacheAdmin(admin.ModelAdmin):
    list_display = '__str__', 'wish_usd_percent_change_24h', 'btc_percent_change_24h', \
                   'eth_percent_change_24h', 'eos_percent_change_24h', 'usd_percent_change_24h'


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    search_fields = 'id', 'name', 'address', 'user.name'
    list_display = '__str__', 'state', 'created_date', 'address', 'last_check', 'active_to'


@admin.register(Heir)
class HeirAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'percentage'


@admin.register(EthContract)
class EthContractAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address'


@admin.register(TokenHolder)
class TokenHolderAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'amount', 'freeze_date'


@admin.register(WhitelistAddress)
class WhitelistAddressAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'active'


@admin.register(NeoContract)
class NeoContractAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address'


@admin.register(SolanaContract)
class SolanaContractAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address'


@admin.register(ContractDetailsToken)
class ContractDetailsTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(ContractDetailsNeo)
class ContractDetailsNeoAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(ContractDetailsAirdrop)
class ContractDetailsAirdropAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address', 'airdrop_in_progress'


@admin.register(ContractDetailsICO)
class ContractDetailsICOAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@admin.register(ContractDetailsNeoICO)
class ContractDetailsNeoICOAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@admin.register(AirdropAddress)
class AirdropAddressAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'amount', 'state', 'active'


@admin.register(TRONContract)
class TRONContractAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address'


admin.site.register(ContractDetailsLastwill)
admin.site.register(ContractDetailsLostKey)
admin.site.register(ContractDetailsDelayedPayment)
admin.site.register(ContractDetailsInvestmentPool)


@admin.register(InvestAddress)
class InvestAddressAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'amount', 'created_date', 'take_away'


@admin.register(EOSTokenHolder)
class EOSTokenHolderAdmin(admin.ModelAdmin):
    list_display = '__str__', 'name', 'address', 'amount', 'freeze_date'


@admin.register(ContractDetailsEOSToken)
class ContractDetailsEOSTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(EOSContract)
class EOSContractAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address'


@admin.register(ContractDetailsEOSAccount)
class ContractDetailsEOSAccountAdmin(admin.ModelAdmin):
    list_display = '__str__', 'account_name', 'owner_public_key', 'active_public_key'


@admin.register(ContractDetailsEOSICO)
class ContractDetailsEOSICOAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@admin.register(EOSAirdropAddress)
class EOSAirdropAddress(admin.ModelAdmin):
    list_display = '__str__', 'address', 'active', 'state', 'amount'


@admin.register(ContractDetailsEOSAirdrop)
class ContractDetailsEOSAirdropAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address'


@admin.register(ContractDetailsEOSTokenSA)
class ContractDetailsEOSTokenSAAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(ContractDetailsTRONToken)
class ContractDetailsTRONTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(ContractDetailsGameAssets)
class ContractDetailsGameAssetsAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'uri'


@admin.register(ContractDetailsTRONAirdrop)
class ContractDetailsTRONAirdropAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address'


admin.site.register(ContractDetailsTRONLostkey)
admin.site.register(ContractDetailsLostKeyTokens)
admin.site.register(ContractDetailsWavesSTO)
admin.site.register(ContractDetailsTokenProtector)
admin.site.register(ApprovedToken)


@admin.register(ProtectorChecker)
class ProtectorCheckerAdmin(admin.ModelAdmin):
    list_display = 'last_check',


admin.site.register(ContractDetailsBinanceLostKeyTokens)


@admin.register(ContractDetailsBinanceToken)
class ContractDetailsBinanceTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


admin.site.register(ContractDetailsBinanceDelayedPayment)
admin.site.register(ContractDetailsBinanceLostKey)
admin.site.register(ContractDetailsBinanceLastwill)
admin.site.register(ContractDetailsBinanceInvestmentPool)


@admin.register(ContractDetailsBinanceICO)
class ContractDetailsBinanceICOAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@admin.register(ContractDetailsBinanceAirdrop)
class ContractDetailsBinanceAirdropAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address', 'airdrop_in_progress'


@admin.register(ContractDetailsMaticICO)
class ContractDetailsMaticICOAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@admin.register(ContractDetailsMaticToken)
class ContractDetailsMaticTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(ContractDetailsMaticAirdrop)
class ContractDetailsMaticAirdropAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address', 'airdrop_in_progress'


@admin.register(ContractDetailsXinFinToken)
class ContractDetailsXinFinTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(ContractDetailsHecoChainToken)
class ContractDetailsHecoChainTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(ContractDetailsHecoChainICO)
class ContractDetailsHecoChainICOAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@admin.register(ContractDetailsMoonriverToken)
class ContractDetailsMoonriverTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@admin.register(ContractDetailsSolanaToken)
class ContractDetailsSolanaTokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'
