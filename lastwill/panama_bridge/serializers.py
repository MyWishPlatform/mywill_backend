from rest_framework.serializers import ModelSerializer

from .models import PanamaTransaction


class UserTransactionSerializer(ModelSerializer):
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