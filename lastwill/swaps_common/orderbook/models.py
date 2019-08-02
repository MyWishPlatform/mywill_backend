from django.contrib.auth.models import User
from django.db import models

from lastwill.contracts.decorators import check_transaction
from lastwill.consts import MAX_WEI_DIGITS


class OrderBookSwaps(models.Model):
    base_address = models.CharField(max_length=50, null=True, default=None)
    base_limit = models.CharField(max_length=512, null=True, default=None)
    base_coin_id = models.IntegerField(default=0)
    quote_address = models.CharField(max_length=50, null=True, default=None)
    quote_limit = models.CharField(max_length=512, null=True, default=None)
    quote_coin_id = models.IntegerField(default=0)
    stop_date = models.DateTimeField()
    public = models.BooleanField(default=True)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    name = models.CharField(max_length=512, null=True)
    state = models.CharField(max_length=63, default='CREATED')
    unique_link = models.CharField(max_length=50, null=True, default=None)
    memo_contract = models.CharField(max_length=70, null=True, default=None)
    user = models.ForeignKey(User)

    broker_fee = models.BooleanField(default=False)
    broker_fee_address = models.CharField(max_length=50, null=True, default=None)
    broker_fee_base = models.FloatField(null=True, default=None)
    broker_fee_quote = models.FloatField(null=True, default=None)

    comment = models.TextField()

    min_base_wei = models.DecimalField(
            max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )
    min_quote_wei = models.DecimalField(
            max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )

    contract_state = models.CharField(max_length=63, default='CREATED')

    @check_transaction
    def msg_deployed(self, message):
        self.contract_state = 'ACTIVE'
        self.save()
        return
