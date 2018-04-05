from django.db import models
from django.contrib.auth.models import User
from lastwill.consts import MAX_WEI_DIGITS

class InternalPayment(models.Model):
    user = models.ForeignKey(User)
    delta = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    tx_hash = models.CharField(max_length=66, null=True, default='')
    datetime = models.DateTimeField(auto_now=True)
    original_currency = models.CharField(max_length=66, null=True, default='')
    original_delta = models.CharField(max_length=66, null=True, default='')

class BTCAccount(models.Model):
    address = models.CharField(max_length=50)
    used = models.BooleanField(default=False)
    balance = models.IntegerField(default=0)
    user = models.ForeignKey(User, null=True, default=None)
