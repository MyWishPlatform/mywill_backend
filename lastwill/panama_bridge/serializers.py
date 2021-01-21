from rest_framework import serializers
from panama_bridge.models import PanamaTransaction


class UserTransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = PanamaTransaction
        fields = (
            'fromNetwork', 'toNetwork', 'actualFromAmount', 'actualToAmount',
            'symbol', 'updateTime', 'status', 'transaction_id',
            'walletFromAddress', 'walletToAddress',
            'walletDepositAddress',
        )