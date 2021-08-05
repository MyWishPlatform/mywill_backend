import threading
import traceback
import sys
import time

import telebot
from django.db import IntegrityError

from lastwill.settings import bot_token
from lastwill.telegram_bot.models import BotSub


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

    def run(self):
        while True:
            try:
                self.bot.polling(none_stop=True)
            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
                time.sleep(15)


bot = Bot(bot_token)
