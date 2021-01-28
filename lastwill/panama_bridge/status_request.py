import requests
from decimal import Decimal
from django.db.models import Q

from .models import PanamaTransaction


BINANCE_BRIDGE_API_URL = "http://api.binance.org/bridge"


# get data about transaction from binance api
def get_status_by_id(panama_trans_id):
    url = "{URL}/api/v1/swaps/{id}".format(
        URL=BINANCE_BRIDGE_API_URL, id=panama_trans_id)
    response = requests.get(url)
    if response.json().get("code") == 20000:
        data = response.json().get("data")
        """ IF response didn't get actualFromAmount and actualToAmount do:
            actualFromAmount = amount
            actualToAmount = amount - networkFee
        """
        try:
            actualFromAmount=Decimal(data.get("actualFromAmount"))
            actualToAmount=Decimal(data.get("actualToAmount"))
        except Exception:
            actualFromAmount=Decimal(data.get("amount"))
            actualToAmount=Decimal(data.get("amount")) - Decimal(data.get("networkFee"))
        else:
            if not actualToAmount or not actualToAmount:
                actualFromAmount = data.get("amount")
                actualToAmount = int(data.get("amount")) - int(data.get("networkFee"))

        return dict(
            fromNetwork=data.get("fromNetwork"),
            toNetwork=data.get("toNetwork"),
            actualFromAmount=actualFromAmount,
            actualToAmount=actualToAmount,
            symbol=data.get("symbol"),
            updateTime=data.get("updateTime"),
            status=data.get("status"),
            transaction_id=data.get("id"),
            walletFromAddress=data.get("walletAddress"),
            walletToAddress=data.get("toAddress"),
            walletDepositAddress=data.get("depositAddress")
        )

# update one db entry
def update_or_create_transaction_status(data):
    if data:
        PanamaTransaction.objects.filter(
            transaction_id=data.get("transaction_id")
        ) \
        .update(
            status=data.get("status"),
            updateTime=data.get("updateTime")
        )


# this is base method to autoupdate transaction status in db
def update_transactions_status():
    # find all database entry with status != completed
    transactions = PanamaTransaction.objects.filter(
        ~Q(status="Completed"), ~Q(status="Cancelled"))

    for trans in transactions:
        # get updating data from binance api
        update_data = get_status_by_id(trans.transaction_id)
        # update local db
        update_or_create_transaction_status(update_data)
