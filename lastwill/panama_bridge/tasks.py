"""
Celery task module.
"""
from lastwill.celery import app

from .services import update_swap_status
from .services_polygon import (second_get_pol_eth_status, update_eth_pol_status, update_pol_eth_status)
from .status_request import update_transactions_status


@app.task()
def update_binance_bridge_transaction_status():
    try:
        update_transactions_status()
    except Exception as exception_error:
        print(f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~')


@app.task()
def update_swap_status_from_backend():
    try:
        update_swap_status()
    except Exception as exception_error:
        print(f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~')


@app.task()
def update_polygon_eth_pol_status():
    try:
        update_eth_pol_status()
    except Exception as exception_error:
        print(f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~')


@app.task()
def update_polygon_pol_eth_status():
    try:
        update_pol_eth_status()
    except Exception as exception_error:
        print(f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~')


@app.task()
def update_polygon_second_pol_eth_status():
    try:
        second_get_pol_eth_status()
    except Exception as exception_error:
        print(f'~~~~~~~~~~~~~~~\n{exception_error}\n~~~~~~~~~~~~~~~')
