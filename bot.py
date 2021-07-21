import threading
import traceback
import sys
import time

import telebot
from django.db import models
from django.db import IntegrityError
from celery_config import app


@app.task
def send_message_to_subs(user, value, site_id):
    subs = BotSub.objects.all()
    bot = telebot.TeleBot(bot_token)
    message = f'[received new payment] user: {user}, value: {value}, site_id: {site_id}'

    for sub in subs:
        try:
            bot.send_message(sub.chat_id, message).message_id
        except Exception:
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)


class BotSub(models.Model):
    chat_id = models.IntegerField(unique=True)


class Bot(threading.Thread):
    def __init__(self, token):
        super().__init__()
        self.bot = telebot.TeleBot(token)

        @self.bot.route('/start ?(.*)')
        def start_handler(message):
            try:
                chat_dest = message['chat']['id']
                BotSub(chat_id=message.chat.id).save()
                self.bot.send_message(chat_dest, 'Hello!')
            except IntegrityError:
                pass

        @self.bot.route('/stop ?(.*)')
        def stop_handler(message):
            try:
                chat_dest = message['chat']['id']
                BotSub.objects.get(chat_id=message.chat.id).delete()
                self.bot.send_message(chat_dest, 'Bye!')
            except BotSub.DoesNotExist:
                pass

        @self.bot.route('/ping ?(.*)')
        def ping_handler(message):
            chat_dest = message['chat']['id']
            self.bot.send_message(chat_dest, 'Pong')

    def run(self):
        while True:
            try:
                self.bot.poll(debug=True)
            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
                time.sleep(15)