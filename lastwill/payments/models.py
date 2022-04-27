from django.contrib.auth.models import User
from django.db import models

from lastwill.consts import MAX_WEI_DIGITS
from lastwill.profile.models import SubSite


class InternalPayment(models.Model):
    user = models.ForeignKey(User)
    delta = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    tx_hash = models.CharField(max_length=66, null=True, default='')
    datetime = models.DateTimeField(auto_now_add=True)
    original_currency = models.CharField(max_length=66, null=True, default='')
    original_delta = models.CharField(max_length=66, null=True, default='')
    site = models.ForeignKey(SubSite)
    fake = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.__str__()} from {self.site.site_name} payment"


class BTCAccount(models.Model):
    address = models.CharField(max_length=50)
    used = models.BooleanField(default=False)
    balance = models.IntegerField(default=0)
    user = models.ForeignKey(User, null=True, default=None)

    def __str__(self):
        return f"{self.user.__str__()} BTC account"


class FreezeBalance(models.Model):
    eosish = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    wish = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    tronish = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    bwish = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)

    def __str__(self):
        return f"ID {self.id}"
