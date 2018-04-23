from time import sleep
import os
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()
from django.contrib.auth.models import User

from lastwill.payments.models import BTCAccount
from lastwill.payments.functions import create_payment
from exchange_API import to_wish


sleep(10)

while 1:
    for user in User.objects.exclude(
            email='', password='', last_name='', first_name=''
    ):
        btc_account = user.btcaccount_set.first()
        if btc_account is None:
            continue
        r = requests.post('http://user:password@127.0.0.1:8332/', json={
                'method': 'getreceivedbyaddress',
                'jsonrpc': '1.0',
                'id': 1,
                'params': [btc_account.address, 5]
        })
        result = json.loads(r.content.decode())['result']
        new_balance = int(result * 10**8)
        if new_balance > btc_account.balance: # enable funds output
            print(user.email, new_balance)
            wish_value = int(to_wish(
                'BTC', (new_balance-btc_account.balance)/10**8
            ) * 10**18)
            BTCAccount.objects.select_for_update().filter(
                id=btc_account.id
            ).update(balance=new_balance)
            create_payment(
                user.id, wish_value, '', 'BTC',
                ((new_balance-btc_account.balance)/10**8) * 10**18
            )
    print('ok')
    sleep(10*60)
