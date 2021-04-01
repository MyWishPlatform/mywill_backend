from django.contrib.admin import ModelAdmin, register
from .actions import export_as_csv_action

from lastwill.panama_bridge.models import (
    PanamaTransaction,
)


@register(PanamaTransaction)
class PanamaTransactionModelAdmin(ModelAdmin):
    """
    Настройки панели администратора модели PanamaTransaction.
    """
    actions = [
        export_as_csv_action(
            "CSV Export",
            fields=[
                'type',
                'from_network',
                'to_network',
                'actual_from_amount',
                'actual_to_amount',
                'eth_symbol',
                'bsc_symbol',
                'update_time',
                'status',
                'transaction_id',
                'wallet_from_address',
                'wallet_to_address',
                'wallet_deposit_address',
            ]
        ),
    ]

    fields = (
        'type',
        'from_network',
        'to_network',
        'actual_from_amount',
        'actual_to_amount',
        'eth_symbol',
        'bsc_symbol',
        'update_time',
        'status',
        'transaction_id',
        'wallet_from_address',
        'wallet_to_address',
        'wallet_deposit_address',
    )
    list_display = (
        'id',
        'type',
        'transaction_id',
        'from_network',
        'to_network',
        'eth_symbol',
        'bsc_symbol',
        'update_time',
        'status',
    )
    list_filter = (
        'type',
        'status',
    )
    search_fields = (
        'id',
        'transaction_id',
        'type',
    )
    ordering = (
        'id',
    )
