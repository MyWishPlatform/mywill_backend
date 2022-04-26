from django.contrib import admin

from .models import (
    InternalPayment,
    BTCAccount,
    FreezeBalance
)

# payments
admin.site.register(InternalPayment)
admin.site.register(BTCAccount)
admin.site.register(FreezeBalance)
