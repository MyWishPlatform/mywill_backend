from django.db import models
from django.contrib.auth.models import User

from lastwill.consts import MAX_WEI_DIGITS


class Promo(models.Model):
    start = models.DateField(null=True, default=None)
    stop = models.DateField(null=True, default=None)
    use_count = models.IntegerField(default=0)
    use_count_max = models.IntegerField(null=True, default=None)
    promo_str = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(User, null=True, default=None, on_delete=models.SET_NULL)
    referral_bonus_usd = models.IntegerField(default=0)
    reusable = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.promo_str} for {self.referral_bonus_usd} USD"


class User2Promo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    contract_id = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.promo.promo_str} for {self.user.__str__()}"


class Promo2ContractType(models.Model):
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE)
    contract_type = models.IntegerField()
    discount = models.IntegerField()
    
    def __str__(self):
        return f"{self.promo.promo_str}"

