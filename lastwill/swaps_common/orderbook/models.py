import random
import string
import smtplib

from django.contrib.auth.models import User
from django.db import models

from lastwill.settings import SITE_PROTOCOL, SWAPS_URL
from lastwill.settings import EMAIL_HOST_USER_SWAPS, EMAIL_HOST_PASSWORD_SWAPS
from lastwill.contracts.decorators import check_transaction
from lastwill.contracts.submodels.swaps import sendEMail
from lastwill.consts import MAX_WEI_DIGITS
from email_messages import *


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
    created_date = models.DateTimeField(auto_now_add=True)
    whitelist = models.BooleanField(default=False)
    whitelist_address = models.CharField(max_length=50)

    @check_transaction
    def msg_deployed(self, message):

        self.contract_state = 'ACTIVE'
        self.save()
        if self.contract.user.email:
            swaps_link = '{protocol}://{url}/public/{unique_link}'.format(
                    protocol=SITE_PROTOCOL,
                    unique_link=self.unique_link, url=SWAPS_URL
            )
            sendEMail(
                    swaps_deploed_subject,
                    swaps_deploed_message.format(swaps_link=swaps_link),
                    [self.contract.user.email]
            )
        return

    def finalized(self, message):
        self.contract_state = 'DONE'
        self.save()

    def cancelled(self, message):
        self.contract_state = 'CANCELLED'
        self.save()


