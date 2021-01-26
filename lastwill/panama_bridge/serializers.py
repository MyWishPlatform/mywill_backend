from rest_framework.serializers import (
    ModelSerializer,
    DateTimeField,
)

from .models import PanamaTransaction


class UserTransactionSerializer(ModelSerializer):
    updateTime = DateTimeField(format="%d-%m-%Y %H:%M")

    class Meta:
        model = PanamaTransaction
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
