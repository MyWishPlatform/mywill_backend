from django.db import models

class DeployAddress(models.Model):
    address = models.CharField(max_length=50)
    locked_by = models.IntegerField(null=True, default=None)
