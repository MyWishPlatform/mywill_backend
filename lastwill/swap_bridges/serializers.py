from rest_framework.serializers import ModelSerializer

from .models import Swap


class SwapModelSerializer(ModelSerializer):
    class Meta:
        model = Swap
        fields = (
            'source_network',
            'target_network',
            'token',
            'source_address',
            'target_address',
            'amount',
            'fee_address',
            'fee_amount',
            'tx_hash',
            'status',
        )
