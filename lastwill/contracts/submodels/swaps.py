import datetime

from ethereum import abi

from django.db import models
from django.core.mail import send_mail, EmailMessage
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *
from lastwill.settings import SUPPORT_EMAIL, CONTRACTS_TEMP_DIR
from lastwill.consts import CONTRACT_PRICE_ETH, NET_DECIMALS, CONTRACT_GAS_LIMIT
from email_messages import *


class InvestAddresses(models.Models):
    contract = models.ForeignKey(Contract)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )

@contract_details('SWAPS contract')
class ContractDetailsSWAPS(CommonDetails):
    swap_address1 = models.CharField(max_length=50)
    swap_value1 = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    swap_address2 = models.CharField(max_length=50)
    swap_value2 = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    active_to = models.DateTimeField()
    public = models.BooleanField(default=True)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    unique_link = models.CharField(max_length=50)

    eth_contract = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='swaps_details',
        on_delete=models.SET_NULL
    )
    temp_directory = models.CharField(max_length=36)
