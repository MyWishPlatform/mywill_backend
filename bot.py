import time
import threading
import traceback
import sys

import telebot
from django.db import models
from django.db import IntegrityError
from celery_config import app
from lastwill.settings import bot_token


@app.task
def send_message_to_subs(user, value, site_id):
    subs = BotSub.objects.all()
    bot = telebot.TeleBot(bot_token)
    message = f'[received new payment] user: {user}, value: {value}, site_id: {site_id}'

    for sub in subs:
        try:
            bot.send_message(sub.chat_id, message).message_id
        except:
            pass


class BotSub(models.Model):
    chat_id = models.IntegerField(unique=True)


class Bot(threading.Thread):
    def __init__(self, token):
        super().__init__()
        self.bot = telebot.TeleBot(token)

        @self.bot.message_handler(commands=['start'])
        def start_handler(message):
            try:
                BotSub(chat_id=message.chat.id).save()
                self.bot.reply_to(message, 'Hello!')
            except IntegrityError:
                pass

        @self.bot.message_handler(commands=['stop'])
        def stop_handler(message):
            try:
                BotSub.objects.get(chat_id=message.chat.id).delete()
                self.bot.reply_to(message, 'Bye!')
            except BotSub.DoesNotExist:
                pass

        @self.bot.message_handler(commands=['ping'])
        def ping_handler(message):
            self.bot.reply_to(message, 'Pong')
