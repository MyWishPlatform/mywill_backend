from lastwill.swaps_common.orderbook.models import OrderBookSwaps
from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField


class OrderBookSwapsModelSerializer(ModelSerializer):
    network = PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = OrderBookSwaps
        fields = (
            'id',
            'name',
            'network',
            'contract_address',
            'base_address',
            'base_limit',
            'base_coin_id',
            'quote_address',
            'quote_limit',
            'quote_coin_id',
            'owner_address',
            'stop_date',
            'memo_contract',
            'unique_link',
            'state',
            'user',
            'public',
            'broker_fee',
            'broker_fee_address',
            'broker_fee_base',
            'broker_fee_quote',
            'comment',
            'min_base_wei',
            'min_quote_wei',
            'contract_state',
            'created_date',
            'state_changed_at',
            'whitelist',
            'whitelist_address',
            'base_amount_contributed',
            'quote_amount_contributed',
            'notification_email',
            'notification_telegram_name',
            'notification',
            'is_rubic_order',
            'rubic_initialized',
        )
