from django.db import models
from lastwill.consts import MAX_WEI_DIGITS


class SnapshotRow(models.Model):
    eth_address = models.CharField(max_length=50)
    value = models.DecimalField(
            max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )

class SnapshotEOSRow(models.Model):
    eos_address = models.CharField(max_length=50)
    value = models.DecimalField(
            max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )


class TRONSnapshotEth(models.Model):
    eth_address = models.CharField(max_length=50)
    balance = models.DecimalField(
            max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )


class TRONSnapshotEOS(models.Model):
    eos_address = models.CharField(max_length=50)
    balance = models.DecimalField(
            max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )


class TRONSnapshotTRON(models.Model):
    tron_address = models.CharField(max_length=50)
    balance = models.DecimalField(
            max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )