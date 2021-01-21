"""
Celery task module.
"""
from rubic_exchange.celery import app

from .status_request import update_transactions_status


@app.task()
def update_binance_bridge_transaction_status():
    try:
        update_transactions_status()
    except Exception as exception_error:
        print(
            f'A$AP!\n~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~'
        )
