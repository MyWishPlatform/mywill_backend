from django.db import models
from django.contrib.auth.models import User

class Promo(models.Model):
    start = models.DateField(null=True, default=None)
    stop = models.DateField(null=True, default=None)
    use_count = models.IntegerField(default=0)
    use_count_max = models.IntegerField(null=True, default=None)
    promo_str = models.CharField(max_length=32, unique=True)


class User2Promo(models.Model):
    user = models.ForeignKey(User)
    promo = models.ForeignKey(Promo)


class Promo2ContractType(models.Model):
    promo = models.ForeignKey(Promo)
    contract_type = models.IntegerField()
    discount = models.IntegerField()
