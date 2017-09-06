import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')

app = Celery('lastwill')

app.autodiscover_tasks()
