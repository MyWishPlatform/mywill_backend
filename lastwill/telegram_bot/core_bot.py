import datetime
import threading
import traceback
import sys
import time

import telebot
from django.db import IntegrityError

from lastwill.settings import bot_token
from lastwill.telegram_bot.models import BotSub
from lastwill.profile.models import UserSiteBalance
from lastwill.deploy.models import Network


def stringify_payment(payment):
    payment_str = f"\nid: {payment.id}\noriginal_currency: {payment.original_currency}\ntx_hash: {payment.tx_hash}\n"
    return payment_str


def contract_stringify_for_contracts_statistics(user, from_date: datetime.date, to_date: datetime.date):
    # return contracts
    pass


def contract_stringify_get_user(contract):
    return f"id: {contract.id}\ncreated_date: {contract.created_date}\ncontract_type: {contract.contract_type}\nnetwork_name: {contract.network.name}\nstate: {contract.state}"


class Bot(threading.Thread):

    MONTHES = ["январь", "февраль", "март", "апрель", "май", "июнь",
               "июль", "август", "сентябрь", "октябрь", "декабрь"]

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

                payments = user_balance.user.internalpayment_set.order_by("-datetime")[:30]
                payments_string_block: str = "".join(stringify_payment(payment) for payment in payments)

                msg = f"User: id {user_balance.user.id}\nemail: {user_balance.user.email}\n\nBalance:\
                \n\nbalance: {user_balance.balance}\nbtc_addr: {user_balance.btc_address}\neth_addr: {user_balance.eth_address}\ntron_addr: {user_balance.tron_address}\nmemo: {user_balance.memo}\n\nPayments:\n{payments_string_block}"

                # TODO: добавить после фиска импорта модели Contract
                # try:
                #     Contract = None
                #     contracts = Contract.objects.filter(network__name__endswith='MAINNET',
                #                                         user__id=user_id)
                #
                #     msg += f"\n\nContracts:\n".join(contract_stringify_get_user(contract) for contract in contracts)
                #
                # except Contract.DoesNotExist:
                #     pass

            except UserSiteBalance.DoesNotExist as ex:
                msg = f"пользователь с таким id не найден"

            except Exception as non_handled_error:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
                msg = '\n'.join(traceback.format_exception(*sys.exc_info()))

            finally:
                self.bot.reply_to(message, msg, parse_mode='html', disable_web_page_preview=True)

        @self.bot.message_handler(commands=["contracts"])
        def contracts_statistics(message):
            # TODO: недописано. Мб удалить
            """
                выгрузка статистики по контрактам с опциями за текущий год. За определённое время
                пример ввода:

                /contracts январь-август
            """
            period_from, period_to = sorted([Bot.MONTHES.index(period) + 1 for period in message.html_text.split()[1].split("-")])
            current_year = datetime.date.today().year

            date_from = datetime.date(day=1, month=period_from, year=current_year)
            date_to = datetime.date(day=1, month=period_to, year=current_year)

            # contracts = Contract.objects.filter(network__name__endswith='MAINNET',
            #                                     deployed_at__gte=from_date,
            #                                     deployed_at__lte=to_date,
            #                                     user__id=user.id)

            # self.bot.reply_to(message, "suchka", parse_mode='html', disable_web_page_preview=True)

            # period_from, period_to

    def run(self):
        while True:
            try:
                self.bot.polling(none_stop=True)

            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
                time.sleep(15)


bot = Bot(bot_token)
