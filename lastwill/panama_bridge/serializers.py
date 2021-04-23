from rest_framework.serializers import (
    CharField,
    DateTimeField,
    DecimalField,
    ModelSerializer,
)

from .models import PanamaTransaction


class UserTransactionSerializer(ModelSerializer):
    fromNetwork = CharField(source='from_network')
    toNetwork = CharField(source='to_network')
    actualFromAmount = DecimalField(
        source='actual_from_amount',
        max_digits=50,
        decimal_places=32,
    )
    actualToAmount = DecimalField(
        source='actual_to_amount',
        max_digits=50,
        decimal_places=32,
    )
    ethSymbol = CharField(source='eth_symbol')
    bscSymbol = CharField(source='bsc_symbol')
    updateTime = DateTimeField(format="%d-%m-%Y %H:%M", source='update_time')
    walletFromAddress = CharField(source='wallet_from_address')
    walletToAddress = CharField(source='wallet_to_address')
    walletDepositAddress = CharField(source='wallet_deposit_address')

    class Meta:
        model = PanamaTransaction
        fields = (
            'type',
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
            'second_transaction_id',
        )
        lookup_field = 'transaction_id'
