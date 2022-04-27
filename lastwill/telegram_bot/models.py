from django.db import models


class BotSub(models.Model):
    chat_id = models.IntegerField(unique=True)

    def __str__(self):
        return f"Chat id {self.chat_id}"
