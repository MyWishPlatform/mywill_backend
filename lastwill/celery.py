import os
from celery import Celery

from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')

app = Celery('mywish',
             broker='amqp://rabbit:rabbit@rabbitmq:5672/rabbit',
             backend='rpc://',
             include=['lastwill.rates.api',
                      'mailings_tasks'])

app.conf.update(result_expires=3600, enable_utc=True, timezone='Europe/Moscow')

app.conf.beat_schedule = {
    'update_rates': {
        'task': 'lastwill.rates.api.update_rates',
        'schedule': crontab(minute=f'*/10'),
    },
    'remind_balance': {
        'task': 'mailings_tasks.remind_balance',
        'schedule': crontab(minute=0, hour=0, day_of_month='*/7'),
    },
}

app.autodiscover_tasks()
