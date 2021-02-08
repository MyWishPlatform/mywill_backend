from django.contrib.admin import ModelAdmin, register, admin
from actions import export_as_csv_action

from lastwill.panama_bridge.models import (
    PanamaTransaction,
)


class CaseAdmin(admin.ModelAdmin):
    ...
    actions = [export_as_csv_action("CSV Export", fields=['field1', 'field2'])]


@register(PanamaTransaction)
class PanamaTransactionModelAdmin(ModelAdmin):
    """
    Настройки панели администратора модели PanamaTransaction.
    """
    actions = [export_as_csv_action("CSV Export",
                                    fields=['fromNetwork', 'toNetwork',
                                            'actualFromAmount', 'actualToAmount',
                                            'ethSymbol', 'bscSymbol', 'updateTime',
                                            'status', 'transaction_id',
                                            'walletFromAddress', 'walletToAddress',
                                            'walletDepositAddress'
                                            ]
                                    )]

    fields = (
        'fromNetwork',
        'toNetwork',
        'actualFromAmount',
        'actualToAmount',
        'ethSymbol',
        'bscSymbol',
        'updateTime',
        'status',
        'transaction_id',
        'walletFromAddress',
        'walletToAddress',
        'walletDepositAddress',
    )
    list_display = (
        'id',
        'transaction_id',
        'fromNetwork',
        'toNetwork',
        'ethSymbol',
        'bscSymbol',
        'updateTime',
        'status',
    )
    list_filter = (
        'status',
    )
    search_fields = (
        'id',
        'transaction_id',
    )
    ordering = (
        'id',
    )
