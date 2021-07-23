import os
import sys


sys.path.append(os.path.abspath(os.path.join(__file__, *[os.pardir] * 3)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()


from lastwill.settings import bot

bot.start()
