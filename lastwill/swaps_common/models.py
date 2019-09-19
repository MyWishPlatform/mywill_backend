from django.db import models
from lastwill.swaps_common.orderbook.models import OrderBookSwaps
from lastwill.contracts.submodels.common import Contract
from lastwill.contracts.submodels.swaps import ContractDetailsSWAPS2


class UnifiedSwapsTable(models.Model):
    swap_id = models.IntegerField()
    swap_type = models.IntegerField()
    order_object = models.ForeignKey(OrderBookSwaps, null=True, default=None)
    # contract_object = models.ForeignKey(Contract, null=True, default=None)
    details_object = models.ForeignKey(ContractDetailsSWAPS2, null=True, default=None)

