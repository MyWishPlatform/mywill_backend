import traceback
import sys

from lastwill.telegram_bot.models import BotSub
from lastwill.telegram_bot.start_bot import bot_instance
from celery_config import app


@app.task
def send_message_to_subs(message):
    subs = BotSub.objects.all()

    for sub in subs:
        try:
            bot_instance.send_message(sub.chat_id, message)
        except Exception:
            print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
