"""
Celery task module.
"""
from lastwill.celery import app

from .orderbook.order_limited.orders import main


@app.task()
def order_limiter():
    try:
        main()
    except Exception as exception_error:
        print(f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~')
