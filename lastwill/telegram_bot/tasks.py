import traceback
import sys

from lastwill.telegram_bot.models import BotSub
from lastwill.settings import bot
from celery_config import app


@app.task
def send_message_to_subs(message):
    subs = BotSub.objects.all()

    for sub in subs:
        try:
            bot.send_message(sub.chat_id, message)
        except Exception:
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
