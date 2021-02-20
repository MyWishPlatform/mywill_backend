"""
Celery task module.
"""
from lastwill.celery import app

from .coingecko_market_sync import sync_data_with_db, add_icon_to_token


@app.task()
def update_coingecko_tokens():
    try:
        sync_data_with_db()
    except Exception as exception_error:
        print(
            f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~'
        )


@app.task()
def update_coingecko_icons():
    try:
        add_icon_to_token()
    except Exception as exception_error:
        print(
            f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~'
        )
