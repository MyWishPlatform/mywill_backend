from django.contrib import admin

from .models import (
    InternalPayment,
    BTCAccount,
    FreezeBalance
)


# payments
@admin.register(InternalPayment)
class InternalPaymentAdmin(admin.ModelAdmin):
    list_display = '__str__', 'original_currency', 'tx_hash', 'datetime', 'fake'


@admin.register(BTCAccount)
class BTCAccountAdmin(admin.ModelAdmin):
    list_display = '__str__', 'address', 'balance', 'used'


@admin.register(FreezeBalance)
class FreezeBalanceAdmin(admin.ModelAdmin):
    list_display = '__str__', 'eosish', 'wish', 'tronish', 'bwish'
