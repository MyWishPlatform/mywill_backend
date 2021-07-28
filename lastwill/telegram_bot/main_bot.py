import threading
import traceback
import sys
import time

import telebot
from django.db import IntegrityError

from lastwill.settings import bot_token
from lastwill.telegram_bot.models import BotSub

# sys.path.append(os.path.abspath(os.path.join(__file__, *[os.pardir] * 3)))
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
# import django
# django.setup()


class Bot(threading.Thread):
    def __init__(self, token):
        super().__init__()
        self.bot = telebot.TeleBot(__name__)
        self.token = token
        self.bot.config['api_key'] = token

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


if __name__ == '__main__':
    bot = Bot(bot_token)
    bot.start()
