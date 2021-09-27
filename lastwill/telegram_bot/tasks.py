import traceback
import sys

from lastwill.telegram_bot.models import BotSub
from django.conf import settings

from celery import shared_task


@shared_task
def send_message_to_subs(message, parse_mode_html=False):
    kwargs = {}
    if parse_mode_html:
        kwargs['parse_mode'] = 'html'

    subs = BotSub.objects.all()
    for sub in subs:
        try:
            settings.bot.send_message(sub.chat_id, message, disable_web_page_preview=True, **kwargs)
        except Exception:
            settings.bot.send_message(sub.chat_id, 'an exception occurred while sending the message')
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            print(message, flush=True)
