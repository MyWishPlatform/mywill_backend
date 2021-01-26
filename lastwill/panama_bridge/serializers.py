import re
from rest_framework.serializers import ModelSerializer, DateField, SerializerMethodField

from .models import PanamaTransaction


class UserTransactionSerializer(ModelSerializer):
    status = SerializerMethodField('change_status_view')
    updateTime = DateField(format="%Y-%m-%d %H:%M")

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
    def change_status_view(self, obj):
        return  re.sub(r"(\w)([A-Z])", r"\1 \2", self.status).capitalize()
