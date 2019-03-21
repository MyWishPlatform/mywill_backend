import datetime

from ethereum import abi

from django.db import models
from django.core.mail import send_mail, EmailMessage
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *


class WavesContract(EthContract):
    pass


@contract_details('Waves STO')
class ContractDetailsICO(CommonDetails):

    soft_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    hard_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    token_name = models.CharField(max_length=512)
    token_short_name = models.CharField(max_length=64)
    admin_address = models.CharField(max_length=50)
    start_date = models.IntegerField()
    stop_date = models.IntegerField()
    rate = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    temp_directory = models.CharField(max_length=36)
    time_bonuses = JSONField(null=True, default=None)
    amount_bonuses = JSONField(null=True, default=None)
    continue_minting = models.BooleanField(default=False)
    cold_wallet_address = models.CharField(max_length=50, default='')
    allow_change_dates = models.BooleanField(default=False)
    whitelist = models.BooleanField(default=False)

    waves_contract = models.ForeignKey(
        WavesContract,
        null=True,
        default=None,
        related_name='waves contract',
        on_delete=models.SET_NULL
    )

    min_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )
    max_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )
