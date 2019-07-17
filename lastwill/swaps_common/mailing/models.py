from django.db import models


class SwapsMailing(models.Model):
    email = models.CharField(max_length=50, null=True, default=None)
    telegram_name = models.CharField(max_length=50, null=True, default=None)
    name = models.CharField(max_length=50, null=True, default=None)
