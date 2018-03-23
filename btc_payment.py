from time import sleep
import os
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

from django.db.models import F
from django.contrib.auth.models import User
from exchange_API import to_wish

from lastwill.payments.models import BTCAccount
from exchange_API import to_wish
from lastwill.profile.models import Profile

sleep(10)

while 1:
    for user in User.objects.exclude(email=''):
        btc_account = user.btcaccount_set.first()
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
            wish_value = int(to_wish('BTC', (new_balance-btc_account.balance)/10**8) * 10**18)
            BTCAccount.objects.select_for_update().filter(id=btc_account.id).update(balance=new_balance)
            Profile.objects.select_for_update().filter(id=user.profile.id).update(balance=F('balance')+wish_value)

    print('ok')
    sleep(10*60)
