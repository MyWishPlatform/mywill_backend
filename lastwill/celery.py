import os
from celery import Celery

from lastwill import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'lastwill.settings',
)

app = Celery(
    main='mywish',
    broker=settings.CELERY_BROKER_URL,
)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object(
    'django.conf:settings',
    namespace='CELERY',
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
