#from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

app = Celery('lastwill')
app.autodiscover_tasks()
