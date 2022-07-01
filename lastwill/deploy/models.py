from django.db import models


class Network(models.Model):
    name = models.CharField(max_length=128, db_index=True)

    def __str__(self):
        return self.name


class DeployAddress(models.Model):
    address = models.CharField(max_length=50)
    locked_by = models.IntegerField(null=True, default=None)
    network = models.ForeignKey(Network, default=1, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.address} to {self.network.name}"
