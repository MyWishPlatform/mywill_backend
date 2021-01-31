from django.db import models


class PanamaTransaction(models.Model):
    """
    Panama bridge transaction model.
    Contains data about user's transaction.
    symbol - field with TOKEN symbol in chain
    """

    fromNetwork = models.CharField(max_length=4)
    toNetwork = models.CharField(max_length=4)
    actualFromAmount = models.DecimalField(
        max_digits=50,
        decimal_places=32
    )
    actualToAmount = models.DecimalField(
        max_digits=50,
        decimal_places=32
    )
    ethSymbol = models.CharField(max_length=6)
    bscSymbol = models.CharField(max_length=6)
    updateTime = models.DateTimeField()
    status = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=33, unique=True)
    walletFromAddress = models.CharField(max_length=42)
    walletToAddress = models.CharField(max_length=42)
    walletDepositAddress = models.CharField(max_length=42)
