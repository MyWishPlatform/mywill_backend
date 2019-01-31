from django.db import models
from django.contrib.auth.models import User
from lastwill.consts import MAX_WEI_DIGITS

class Profile(models.Model):
    user = models.OneToOneField(User)
    balance = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, default=0)
    eos_balance = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, default=0)
    internal_address = models.CharField(max_length=50, null=True, default=None)
    internal_btc_address = models.CharField(max_length=50, null=True, default=None)
    totp_key = models.CharField(max_length=16, null=True, default=None)
    use_totp = models.BooleanField(default=False)
    is_social = models.BooleanField(default=False)
    lang = models.CharField(max_length=2, default='en')
    last_used_totp = models.CharField(max_length=64, null=True, default=None)
    memo = models.CharField(max_length=25, null=True, default=None, unique=True)


class SubSite(models.Model):
    site_name = models.CharField(max_length=35, null=True, default=None)
    currencies = models.CharField(max_length=80, null=True, default=None)


class UserSiteBalance(models.Model):
    user = models.ForeignKey(User)
    subsite = models.ForeignKey(SubSite)
    balance = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, default=0)
    eth_address = models.CharField(max_length=50, null=True, default=None)
    btc_address = models.CharField(max_length=50, null=True, default=None)
    memo = models.CharField(max_length=25, null=True, default=None, unique=True)


class APIToken(models.Model):
    user = models.ForeignKey(User)
    token = models.CharField(max_length=36)
    comment = models.CharField(max_length=50, null=True, default=None)

    class Meta:
        unique_together = ("user", "token")
