from django.db import models


class BotSub(models.Model):
    chat_id = models.IntegerField(unique=True)
