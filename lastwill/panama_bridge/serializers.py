from rest_framework.serializers import (
    DateTimeField,
    ModelSerializer,
    SerializerMethodField,
)

from .models import PanamaTransaction


class UserTransactionSerializer(ModelSerializer):
    updateTime = DateTimeField(format="%d-%m-%Y %H:%M")
    actualToAmount = SerializerMethodField("get_normalize_ATA")
    actualFromAmount = SerializerMethodField("get_normalize_AFA")

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

    def get_normalize_ATA(self, obj):
        return obj.actualToAmount.normalize()

    def get_normalize_AFA(self, obj):
        return obj.actualFromAmount.normalize()
