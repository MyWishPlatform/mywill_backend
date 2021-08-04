import traceback
import sys

from lastwill.telegram_bot.models import BotSub
from lastwill.telegram_bot.main_bot import bot
from celery import shared_task


@shared_task
def send_message_to_subs(message, **kwargs):

    subs = BotSub.objects.all()
    for sub in subs:
        try:
            bot.bot.send_message(sub.chat_id, message, disable_web_page_preview=True, **kwargs)
        except Exception:
            bot.bot.send_message(sub.chat_id, 'an exception occurred while sending the message')
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            print(message, flush=True)
