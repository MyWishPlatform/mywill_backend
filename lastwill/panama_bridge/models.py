from django.db import models


class PanamaTransaction(models.Model):
    """
    Panama bridge transaction model.
    Contains data about user's transaction.
    symbol - field with TOKEN symbol in chain
    """

    fromNetwork = models.CharField(max_length=4)
    toNetwork = models.CharField(max_length=4)
    actualFromAmount = models.FloatField()
    actualToAmount = models.FloatField()
    symbol = models.CharField(max_length=4)
    updateTime = models.DateTimeField()
    status = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=33)
    walletFromAddress = models.CharField(max_length=42)
    walletToAddress = models.CharField(max_length=42)
    walletDepositAddress = models.CharField(max_length=42)

