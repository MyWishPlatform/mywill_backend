import sys
import os
from pathlib import Path

sys.path.append(Path(__file__).resolve().parents[2].resolve().as_posix())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django

django.setup()

from django.conf import settings
from lastwill.telegram_bot.core_bot import init_bot

init_bot()

if __name__ == '__main__':
    settings.bot.start()
