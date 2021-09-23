import threading
import traceback
import sys
import time

import telebot
from django.db import IntegrityError

from lastwill.settings import bot_token
from lastwill.telegram_bot.models import BotSub
from lastwill.profile.models import UserSiteBalance


def stringify_payment(payment):
    print(f"tx_hash {payment.tx_hash}")
    payment_str = f"\nid: {payment.id}\noriginal_currency: {payment.original_currency}\ntx_hash: {payment.tx_hash}"
    return payment_str


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

        @self.bot.message_handler(commands=['users'])
        def get_user(message):
            """
                позволяет достать из базы данных пользователя по внутреннему id
            """
            msg = ""

            try:
                user_id: int = int(message.html_text[7:])
                user_balance = UserSiteBalance.objects.get(user__id=user_id, subsite=1)

                payments = user_balance.user.internalpayment_set.all()
                payments_string_block: str = "".join(stringify_payment(payment) for payment in payments)

                msg = f"User: id {user_balance.user.id}\nemail: {user_balance.user.email}\n\nBalance:\
                \n\nbalance: {user_balance.balance}\nbtc_addr: {user_balance.btc_address}\neth_addr: {user_balance.eth_address}\ntron_addr: {user_balance.tron_address}\nmemo: {user_balance.memo}\n\nPayments:\n{payments_string_block}"

            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
                msg = '\n'.join(traceback.format_exception(*sys.exc_info()))
                # msg = "неправильный ввод"

            finally:
                self.bot.reply_to(message, msg, parse_mode='html', disable_web_page_preview=True)

    def run(self):
        while True:
            try:
                self.bot.polling(none_stop=True)

            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
                time.sleep(15)


bot = Bot(bot_token)
