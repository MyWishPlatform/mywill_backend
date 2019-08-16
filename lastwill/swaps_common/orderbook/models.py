import random
import string
import smtplib

from django.contrib.auth.models import User
from django.db import models

from lastwill.settings import SITE_PROTOCOL, SWAPS_URL
from lastwill.settings import EMAIL_HOST_USER_SWAPS, EMAIL_HOST_PASSWORD_SWAPS
from lastwill.contracts.decorators import check_transaction
from lastwill.contracts.submodels.swaps import sendEMail
from lastwill.contracts.submodels.common import Contract
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

    min_base_wei = models.CharField(max_length=512, default=None, null=True)
    min_quote_wei = models.CharField(max_length=512, default=None, null=True)

    contract_state = models.CharField(max_length=63, default='CREATED')
    created_date = models.DateTimeField(auto_now_add=True)
    whitelist = models.BooleanField(default=False)
    whitelist_address = models.CharField(max_length=50)
    swap_ether_contract = models.ForeignKey(Contract, null=True)

    base_amount_contributed = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, default=0)
    base_amount_total = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, default=0)
    quote_amount_contributed = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, default=0)
    quote_amount_total = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, default=0)

    def deposit_order(self, message):
        msg_amount = message['amount']
        if message['token'] == self.base_address or message['token'] == self.quote_address:
            if message['token'] == self.base_address:
                self.base_amount_contributed += msg_amount
                self.base_amount_total += msg_amount
            else:
                self.quote_amount_contributed += msg_amount
                self.quote_amount_total += msg_amount

            self.save()

    def refund_order(self, message):
        msg_amount = message['amount']
        if message['token'] == self.base_address or message['token'] == self.quote_address:
            if message['token'] == self.base_address:
                self.quote_amount_contributed -= msg_amount
            else:
                self.base_amount_contributed -= msg_amount

            self.save()

    @check_transaction
    def msg_deployed(self, message):

        self.state = 'ACTIVE'
        self.swap_ether_contract.state = 'ACTIVE'
        self.contract_state = self.swap_ether_contract.state
        self.save()
        if self.user.email:
            swaps_link = '{protocol}://{url}/public/{unique_link}'.format(
                    protocol=SITE_PROTOCOL,
                    unique_link=self.unique_link, url=SWAPS_URL
            )
            sendEMail(
                    swaps_deploed_subject,
                    swaps_deploed_message.format(swaps_link=swaps_link),
                    [self.user.email]
            )
        return

    def finalized(self, message):
        self.state = 'DONE'
        self.swap_ether_contract.state = 'DONE'
        self.contract_state = self.swap_ether_contract.state
        self.save()

    def cancelled(self, message):
        self.state = 'CANCELLED'
        self.swap_ether_contract.state = 'CANCELLED'
        self.contract_state = self.swap_ether_contract.state
        self.save()


