import binascii
import bitcoin
import requests


import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
import django
django.setup()

from lastwill.payments.models import BTCAccount

while 1:
    try:
        btc_priv = input()
    except EOFError:
        break

    btc_pub = bitcoin.privtopub(btc_priv)
    btc_addr = bitcoin.pubtoaddr(btc_pub)

    r = requests.post(
            'http://user:password@127.0.0.1:8332/',
            json={'method': 'importaddress', 'params': [btc_addr, btc_addr, False], 'id': 1, 'jsonrpc': '1.0'}
    )    
    print(btc_addr, r.content)

    b = BTCAccount(address = btc_addr)
    b.save()
