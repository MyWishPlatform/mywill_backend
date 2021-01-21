import requests

from django.db.models import Q

from .models import PanamaTransaction


API_PANAMA = "http://api.binance.org/bridge"


# get data about transaction from binance api
def get_status_by_id(panama_trans_id):

    response = requests.get(API_PANAMA+"/api/v1/swaps/"+panama_trans_id)
    if response.json().get("code")==20000:
        data = response.json().get("data")
        return dict(
            fromNetwork=data.get("fromNetwork"),
            toNetwork=data.get("toNetwork"),
            actualFromAmount=data.get("actualFromAmount"),
            actualToAmount=data.get("actualToAmount"),
            symbol=data.get("symbol"),
            updateTime=data.get("updateTime"),
            status=data.get("status"),
            transaction_id=data.get("id"),
            walletFromAddress=data.get("walletAddress"),
            walletToAddress=data.get("toAddress"),
            walletDepositAddress=data.get("depositAddress")
        )
    else:
        return None

# update one db entry
def update_or_create_transaction_status(data):
    if data is not None:
        transaction = PanamaTransaction.objects.update_or_create(
            transaction_id = data.get("transaction_id"),
            defaults=dict(
                fromNetwork=data.get("fromNetwork"),
                toNetwork = data.get("toNetwork"),
                actualFromAmount = data.get("actualFromAmount"),
                actualToAmount = data.get("actualToAmount"),
                symbol = data.get("symbol"),
                updateTime = data.get("updateTime"),
                status = data.get("status"),
                walletFromAddress = data.get("walletFromAddress"),
                walletToAddress = data.get("walletToAddress"),
                walletDepositAddress = data.get("walletDepositAddress"),
            )
        )
    else:
        pass


# this is base method to autoupdate transaction status in db
# TO DO add celery
def update_transactions_status():
    # find all database entry with status != completed
    transactions = PanamaTransaction.objects.filter(~Q(status="completed"))
    for trans in transactions:
        # take transaction_id with status != completed
        trans_id = trans.transaction_id
        # get updating data from binance api
        update_data = get_status_by_id(trans_id)
        # update local db
        update_or_create_transaction_status(update_data)


# method to create db entry for new transaction
def make_status(panama_trans_id):
    data = get_status_by_id(panama_trans_id)
    print(data)
    update_or_create_transaction_status(data)


# test data
# panama_trans_id = "e6e0c42fa1dd4c9eba8bfcf24465ec56"
# make_status(panama_trans_id)
