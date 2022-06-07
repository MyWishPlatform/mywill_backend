from django.contrib.admin import ModelAdmin, register

# New import 28.04.2022
from lastwill.contracts.models import (
    AirdropAddress, ApprovedToken, Contract, ContractDetailsAirdrop, ContractDetailsBinanceAirdrop,
    ContractDetailsBinanceDelayedPayment, ContractDetailsBinanceICO, ContractDetailsBinanceInvestmentPool,
    ContractDetailsBinanceLastwill, ContractDetailsBinanceLostKey, ContractDetailsBinanceLostKeyTokens,
    ContractDetailsBinanceToken, ContractDetailsDelayedPayment, ContractDetailsEOSAccount, ContractDetailsEOSAirdrop,
    ContractDetailsEOSICO, ContractDetailsEOSToken, ContractDetailsEOSTokenSA, ContractDetailsGameAssets,
    ContractDetailsHecoChainICO, ContractDetailsHecoChainToken, ContractDetailsICO, ContractDetailsInvestmentPool,
    ContractDetailsLastwill, ContractDetailsLostKey, ContractDetailsLostKeyTokens, ContractDetailsMaticAirdrop,
    ContractDetailsMaticICO, ContractDetailsMaticToken, ContractDetailsMoonriverToken, ContractDetailsNeo,
    ContractDetailsNeoICO, ContractDetailsSolanaToken, ContractDetailsToken, ContractDetailsTokenProtector,
    ContractDetailsTRONAirdrop, ContractDetailsTRONLostkey, ContractDetailsTRONToken, ContractDetailsWavesSTO,
    ContractDetailsXinFinToken, CurrencyStatisticsCache, EOSAirdropAddress, EOSContract, EOSTokenHolder, EthContract,
    Heir, InvestAddress, NeoContract, ProtectorChecker, SolanaContract, TokenHolder, TRONContract, WhitelistAddress)
from lastwill.swaps_common.tokentable.models import (CoinGeckoToken, Tokens, TokensCoinMarketCap, TokensUpdateTime)


@register(Tokens)
class TokensModelAdmin(ModelAdmin):
    """
    Настройки панели администратора модели Token.
    """
    fields = (
        'address',
        'token_name',
        'token_short_name',
        'decimals',
        'image_link',
    )
    list_display = (
        'id',
        'address',
        'token_name',
        'token_short_name',
        'decimals',
        'image_link',
    )
    search_fields = (
        'id',
        'token_short_name',
        'address',
    )
    ordering = ('id',)


@register(TokensCoinMarketCap)
class TokensCoinMarketCapModelAdmin(ModelAdmin):
    """
    Настройки панели администратора модели TokensCoinMarketCap.
    """
    fields = (
        'token_name',
        'token_short_name',
        'token_platform',
        'token_address',
        'image',
    )
    list_display = (
        'id',
        'token_cmc_id',
        'token_short_name',
        'token_platform',
        'token_address',
        'token_rank',
        'token_price',
        'updated_at',
        'is_displayed',
    )
    list_filter = (
        'updated_at',
        'is_displayed',
    )
    search_fields = (
        'token_cmc_id',
        'token_name',
        'token_short_name',
        'token_platform',
        'token_address',
    )
    ordering = ('id',)


@register(CoinGeckoToken)
class CoinGeckoTokenModelAdmin(ModelAdmin):
    """
    Настройки панели администратора модели CoinGeckoToken.
    """
    fields = (
        'title',
        'short_title',
        'address',
        'platform',
        'decimals',
        'source_image_link',
        'image_file',
        'rank',
        'usd_price',
        'is_native',
        'is_displayed',
        'used_in_iframe',
    )
    list_display = (
        'id',
        'title',
        'short_title',
        'platform',
        'address',
        'created_at',
        'updated_at',
        'is_native',
        'is_displayed',
        'used_in_iframe',
    )
    list_filter = (
        'platform',
        'created_at',
        'updated_at',
        'is_native',
        'is_displayed',
        'used_in_iframe',
    )
    search_fields = (
        'title',
        '=short_title',
        '=address',
    )
    ordering = ('id',)


@register(TokensUpdateTime)
class TokensUpdateTimeModelAdmin(ModelAdmin):
    """
    Настройки панели администратора модели TokensUpdateTime.
    """
    fields = ()
    list_display = (
        'id',
        'last_time_updated',
    )
    list_filter = ('last_time_updated',)
    search_fields = ('id',)
    ordering = ('id',)


#######################
#                     #
# New code 28.04.2022 #
#                     #
#######################


# contracts
@register(CurrencyStatisticsCache)
class CurrencyStatisticsCacheAdmin(ModelAdmin):
    list_display = '__str__', 'wish_usd_percent_change_24h', 'btc_percent_change_24h', \
                   'eth_percent_change_24h', 'eos_percent_change_24h', 'usd_percent_change_24h'


@register(Contract)
class ContractAdmin(ModelAdmin):
    search_fields = 'id', 'name', 'address', 'user_address'
    list_display = '__str__', 'state', 'created_date', 'address', 'last_check', 'active_to'


@register(Heir)
class HeirAdmin(ModelAdmin):
    list_display = '__str__', 'address', 'percentage'


@register(EthContract)
class EthContractAdmin(ModelAdmin):
    list_display = '__str__', 'address'


@register(TokenHolder)
class TokenHolderAdmin(ModelAdmin):
    list_display = '__str__', 'address', 'amount', 'freeze_date'


@register(WhitelistAddress)
class WhitelistAddressAdmin(ModelAdmin):
    list_display = '__str__', 'address', 'active'


@register(NeoContract)
class NeoContractAdmin(ModelAdmin):
    list_display = '__str__', 'address'


@register(SolanaContract)
class SolanaContractAdmin(ModelAdmin):
    list_display = '__str__', 'address'


@register(ContractDetailsToken)
class ContractDetailsTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsNeo)
class ContractDetailsNeoAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsAirdrop)
class ContractDetailsAirdropAdmin(ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address', 'airdrop_in_progress'


@register(ContractDetailsICO)
class ContractDetailsICOAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@register(ContractDetailsNeoICO)
class ContractDetailsNeoICOAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@register(AirdropAddress)
class AirdropAddressAdmin(ModelAdmin):
    list_display = '__str__', 'address', 'amount', 'state', 'active'


@register(TRONContract)
class TRONContractAdmin(ModelAdmin):
    list_display = '__str__', 'address'


@register(ContractDetailsLastwill)
class ContractDetailsLastwillAdmin(ModelAdmin):
    list_display = '__str__', 'user_address', 'email', 'btc_key'


@register(ContractDetailsLostKey)
class ContractDetailsLostKeyAdmin(ModelAdmin):
    list_display = '__str__', 'user_address', 'active_to'


@register(ContractDetailsDelayedPayment)
class ContractDetailsDelayedPaymentAdmin(ModelAdmin):
    list_display = '__str__', 'date', 'user_address', 'recepient_address', 'recepient_email'


@register(ContractDetailsInvestmentPool)
class ContractDetailsInvestmentPoolAdmin(ModelAdmin):
    list_display = '__str__', 'admin_address', 'whitelist'


@register(ContractDetailsLostKeyTokens)
class ContractDetailsLostKeyTokensAdmin(ModelAdmin):
    list_display = '__str__', 'user_address', 'email'


@register(InvestAddress)
class InvestAddressAdmin(ModelAdmin):
    list_display = '__str__', 'address', 'amount', 'created_date', 'take_away'


@register(EOSTokenHolder)
class EOSTokenHolderAdmin(ModelAdmin):
    list_display = '__str__', 'name', 'address', 'amount', 'freeze_date'


@register(ContractDetailsEOSToken)
class ContractDetailsEOSTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(EOSContract)
class EOSContractAdmin(ModelAdmin):
    list_display = '__str__', 'address'


@register(ContractDetailsEOSAccount)
class ContractDetailsEOSAccountAdmin(ModelAdmin):
    list_display = '__str__', 'account_name', 'owner_public_key', 'active_public_key'


@register(ContractDetailsEOSICO)
class ContractDetailsEOSICOAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@register(EOSAirdropAddress)
class EOSAirdropAddress(ModelAdmin):
    list_display = '__str__', 'address', 'active', 'state', 'amount'


@register(ContractDetailsEOSAirdrop)
class ContractDetailsEOSAirdropAdmin(ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address'


@register(ContractDetailsEOSTokenSA)
class ContractDetailsEOSTokenSAAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsTRONToken)
class ContractDetailsTRONTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsGameAssets)
class ContractDetailsGameAssetsAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'uri'


@register(ContractDetailsTRONAirdrop)
class ContractDetailsTRONAirdropAdmin(ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address'


@register(ContractDetailsTRONLostkey)
class ContractDetailsTRONLostkeyAdmin(ModelAdmin):
    list_display = '__str__', 'user_address', 'active_to'


@register(ContractDetailsWavesSTO)
class ContractDetailsWavesSTOAdmin(ModelAdmin):
    list_display = '__str__', 'admin_address', 'start_date', 'stop_date'


@register(ContractDetailsTokenProtector)
class ContractDetailsTokenProtectorAdmin(ModelAdmin):
    list_display = '__str__', 'owner_address', 'reserve_address', 'email'


@register(ApprovedToken)
class ApprovedTokenAdmin(ModelAdmin):
    list_display = '__str__', 'address', 'is_confirmed', 'approve_from_scanner', 'approve_from_front'


@register(ProtectorChecker)
class ProtectorCheckerAdmin(ModelAdmin):
    list_display = 'last_check',


@register(ContractDetailsBinanceToken)
class ContractDetailsBinanceTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsBinanceLostKeyTokens)
class ContractDetailsBinanceLostKeyTokensAdmin(ModelAdmin):
    list_display = '__str__', 'user_address', 'email'


@register(ContractDetailsBinanceDelayedPayment)
class ContractDetailsBinanceDelayedPaymentAdmin(ModelAdmin):
    list_display = '__str__', 'date', 'user_address', 'recepient_address', 'recepient_email'


@register(ContractDetailsBinanceLostKey)
class ContractDetailsBinanceLostKeyAdmin(ModelAdmin):
    list_display = '__str__', 'user_address', 'active_to'


@register(ContractDetailsBinanceInvestmentPool)
class ContractDetailsBinanceInvestmentPoolAdmin(ModelAdmin):
    list_display = '__str__', 'admin_address', 'whitelist'


@register(ContractDetailsBinanceLastwill)
class ContractDetailsBinanceLastwillAdmin(ModelAdmin):
    list_display = '__str__', 'user_address', 'email', 'btc_key'


@register(ContractDetailsBinanceICO)
class ContractDetailsBinanceICOAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@register(ContractDetailsBinanceAirdrop)
class ContractDetailsBinanceAirdropAdmin(ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address', 'airdrop_in_progress'


@register(ContractDetailsMaticICO)
class ContractDetailsMaticICOAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@register(ContractDetailsMaticToken)
class ContractDetailsMaticTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsMaticAirdrop)
class ContractDetailsMaticAirdropAdmin(ModelAdmin):
    list_display = '__str__', 'token_address', 'admin_address', 'airdrop_in_progress'


@register(ContractDetailsXinFinToken)
class ContractDetailsXinFinTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsHecoChainToken)
class ContractDetailsHecoChainTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsHecoChainICO)
class ContractDetailsHecoChainICOAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'start_date', 'stop_date'


@register(ContractDetailsMoonriverToken)
class ContractDetailsMoonriverTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'


@register(ContractDetailsSolanaToken)
class ContractDetailsSolanaTokenAdmin(ModelAdmin):
    list_display = '__str__', 'token_short_name', 'admin_address', 'white_label'
