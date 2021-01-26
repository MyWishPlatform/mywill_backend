import requests

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
            actualFromAmount=data.get("actualFromAmount")
            actualToAmount=data.get("actualToAmount")
        except Exception:
            actualFromAmount=data.get("amount")
            actualToAmount=int(data.get("amount")) - int(data.get("networkFee"))
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
        transaction = PanamaTransaction.objects.update_or_create(
            transaction_id=data.get("transaction_id"),
            defaults=dict(
                fromNetwork=data.get("fromNetwork"),
                toNetwork=data.get("toNetwork"),
                actualFromAmount=data.get("actualFromAmount"),
                actualToAmount=data.get("actualToAmount"),
                symbol=data.get("symbol"),
                updateTime=data.get("updateTime"),
                status=data.get("status"),
                walletFromAddress=data.get("walletFromAddress"),
                walletToAddress=data.get("walletToAddress"),
                walletDepositAddress=data.get("walletDepositAddress"),
            )
        )


# this is base method to autoupdate transaction status in db
# TODO add celery
def update_transactions_status():
    # find all database entry with status != completed
    transactions = PanamaTransaction.objects.filter(
        ~Q(status="Completed"), ~Q(status="Cancelled"))
    for trans in transactions:
        # take transaction_id with status != completed
        trans_id = trans.transaction_id
        # get updating data from binance api
        update_data = get_status_by_id(trans_id)
        # update local db
        update_or_create_transaction_status(update_data)
