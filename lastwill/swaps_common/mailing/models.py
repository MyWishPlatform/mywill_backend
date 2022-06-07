from django.db import models

from lastwill.profile.models import User


class SwapsMailing(models.Model):
    email = models.CharField(max_length=50, null=True, default=None)
    telegram_name = models.CharField(max_length=50, null=True, default=None)
    name = models.CharField(max_length=50, null=True, default=None)


class SwapsNotificationDefaults(models.Model):
    user = models.ForeignKey(User)
    email = models.CharField(max_length=50, null=True, default=None)
    telegram_name = models.CharField(max_length=50, null=True, default=None)
    notification = models.BooleanField(default=False)
