#from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()
from django.utils import timezone
from lastwill.checker import check_all

app = Celery('lastwill')


# @app.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_periodic_task(
#         crontab(hour=12, minute=0),
#         check_task,
#     )

app.autodiscover_tasks()

# @app.task(bind=True)
# def check_task(self):
#     check_all()
