from django.db import models
from django.contrib.auth.models import User

from lastwill.consts import MAX_WEI_DIGITS


class Promo(models.Model):
    start = models.DateField(null=True, default=None)
    stop = models.DateField(null=True, default=None)
    use_count = models.IntegerField(default=0)
    use_count_max = models.IntegerField(null=True, default=None)
    promo_str = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(User, null=True, default=None)
    referral_bonus_usd = models.IntegerField(default=0)
    reusable = models.BooleanField(default=False)


class User2Promo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    contract_id = models.IntegerField(default=0)


class Promo2ContractType(models.Model):
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE)
    contract_type = models.IntegerField()
    discount = models.IntegerField()
