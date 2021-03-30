"""
Celery task module.
"""
from lastwill.celery import app

from .services import update_swap_status


@app.task()
def update_swap_status_from_backend():
    try:
        update_swap_status()
    except Exception as exception_error:
        print(
            f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~'
        )
