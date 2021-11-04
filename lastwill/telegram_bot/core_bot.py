import datetime
import threading
import traceback
import sys
import time

import telebot
from django.conf import settings
from django.db import IntegrityError

from lastwill.contracts.submodels.common import Contract, CommonDetails
from lastwill.payments.api import get_payment_statistics
from lastwill.promo.models import Promo
from lastwill.settings import bot_token
from lastwill.telegram_bot.models import BotSub
from lastwill.profile.models import UserSiteBalance


def stringify_payment(payment):
    payment_str = f"\nid: {payment.id}\noriginal_currency: {payment.original_currency}\ntx_hash: {payment.tx_hash}\n"
    return payment_str


def contract_stringify_for_contracts_statistics(stat: dict):
    # "objects": [c],
    # "verification": 0,
    # "white_label": 0,
    # "cost": 0})
    return f"<b>{stat['name']}</b> contracts: {stat['count']} cost: {stat['cost']} whitelabel: {stat['white_label']}" \
           f" verification: {stat['verification']}\n\n"


def contract_stringify_get_user(contract: Contract):
    return "" + \
    f"id: {contract.id}\n" + \
    f"created_date: {contract.created_date}\n" + \
    f"contract_type: {contract.contract_type}\n" + \
    f"network: {contract.network}\n" + \
    f"state: {contract.state}\n\n"


def promo_stringify_monthes(promo: Promo):
    return f"{promo.promo_str} {promo.use_count} contracts for {promo.referral_bonus_usd * promo.use_count} usd\n"


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

                payments = user_balance.user.internalpayment_set.order_by("-datetime")[:15]
                payments_string_block: str = "".join(stringify_payment(payment) for payment in payments)

                msg = f"User: id {user_balance.user.id}\nemail: {user_balance.user.email}\n\nBalance:\
                \n\nbalance: {user_balance.balance}\nbtc_addr: {user_balance.btc_address}\neth_addr: {user_balance.eth_address}\ntron_addr: {user_balance.tron_address}\nmemo: {user_balance.memo}\n\nPayments:\n{payments_string_block}"

                # TODO: добавить после фиска импорта модели Contract
                try:
                    contracts = Contract.objects.filter(network__name__endswith='MAINNET',
                                                        user__id=user_id)

                    msg += "\n\n<b>Contracts:</b>\n\n" + "".join(contract_stringify_get_user(contract) for contract in contracts[:15])

                except Contract.DoesNotExist:
                    pass

            except UserSiteBalance.DoesNotExist as ex:
                msg = f"пользователь с таким id не найден"

            except Exception as non_handled_error:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
                msg = '\n'.join(traceback.format_exception(*sys.exc_info()))

            finally:
                self.bot.reply_to(message, msg, parse_mode='html', disable_web_page_preview=True)

        @self.bot.message_handler(commands=["monthly", "weekly"])
        def contracts_statistics(message):
            """
                выгрузка статистики по контрактам с опциями за текущий год. За определённое время
                пример ввода:

                /monthly январь-август
            """

            # платежи
            current_year = datetime.date.today().year
            current_month = datetime.date.today().month
            current_day = datetime.date.today().day

            period_from, period_to = None, None

            if "monthly" in message.html_text:
                period_from, period_to = sorted([Bot.MONTHES.index(period) + 1 for period in message.html_text.split()[1].split("-")])
                date_from = datetime.date(day=1, month=period_from, year=current_year)
                date_to = datetime.date(day=1, month=period_to, year=current_year)

            elif "weekly" in message.html_text:
                date_from = datetime.date(day=current_day, month=current_month, year=current_year) - datetime.timedelta(days=7)
                date_to = datetime.date(day=current_day, month=current_month, year=current_year)


            self.bot.reply_to(message, "Подождите. Производится сбор информации", parse_mode='html',
                              disable_web_page_preview=True)

            payment_statistics = get_payment_statistics(start=date_from, stop=date_to, only_total=True)

            msg = f"PAYMENTS\n\nETH {payment_statistics['ETH']}\nBNB {payment_statistics['BNB']}\nBSCBNB {payment_statistics['BSCBNB']}\nTRX {payment_statistics['TRX']}"
            self.bot.reply_to(message, msg, parse_mode='html', disable_web_page_preview=True)


            # промокоды
            msg = ""
            promocodes = Promo.objects.filter(
                start__isnull=False,
                start__gt=date_from,
                use_count__gt=0
            )


            msg = "Promocodes: " + "".join(promo_stringify_monthes(promo) for promo in promocodes)

            self.bot.reply_to(message, msg, parse_mode='html', disable_web_page_preview=True)


            # контракты
            msg = "<b>Contracts MAINNET:</b>\n\n"
            contracts = Contract.objects.filter(network__name__endswith='MAINNET',
                                                deployed_at__gte=date_from,
                                                deployed_at__lte=date_to)

            contracts_statistics = []
            index = None

            for c in contracts:
                try:
                    index = contracts_statistics.index(c.name)
                    contracts_statistics[index].update(
                        {
                            "count": contracts_statistics[index]["count"] + 1,
                            "objects": [*contracts_statistics[index]["objects"], c],
                        })

                except ValueError:
                    contracts_statistics.append({"name": c.name,
                                                 "count": 1,
                                                 "objects": [c],
                                                 "verification": 0,
                                                 "white_label": 0,
                                                 "cost": 0})
                    index = len(contracts_statistics) - 1

                finally:
                    c_details = c.get_details()
                    cost = c_details.calc_cost({"verification": True}, network=c.network)
                    white_label_new_quantity = contracts_statistics[index]["white_label"] if c_details.white_label \
                        else contracts_statistics[index]["white_label"]

                    verification = c_details.verification

                    contracts_statistics[index].update({
                        "cost": contracts_statistics[index]["cost"] + 1,
                        "white_label": white_label_new_quantity,
                        "verification": contracts_statistics[index]["verification"] + 1
                    })

            msg += "".join(contract_stringify_for_contracts_statistics(stat) for stat in contracts_statistics[:60])
            # TODO: добавить Contracts TESTNET
            self.bot.reply_to(message, msg, parse_mode='html', disable_web_page_preview=True)



    def run(self):
        while True:
            try:
                self.bot.polling(none_stop=True)

            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
                time.sleep(15)


def init_bot():
    settings.bot = Bot(bot_token)
