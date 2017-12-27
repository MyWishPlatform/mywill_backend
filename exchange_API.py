import requests
import json
import time

class memoize_timeout:
    def __init__(self, timeout):
        self.timeout = timeout
        self.cache = {}

    def __call__(self, f):
        def func(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            v = self.cache.get(key, (0,0))
            print('cache')
            if time.time() - v[1] > self.timeout:
                print('updating')
                v = self.cache[key] = f(*args, **kwargs), time.time()
            return v[0]
        return func

'''
def wish_to_btc():
    return float(json.loads(requests.get(
            'https://api.coinmarketcap.com/v1/ticker/mywish/'
    ).content.decode())[0]['price_btc'])

@memoize_timeout(10*60)
def wish_to_curr(curr):
    wish_btc = wish_to_btc()
    if curr == 'BTC':
        return wish_btc
    btc_to_curr = float(json.loads(requests.get(
            'https://api.coinmarketcap.com/v1/ticker/bitcoin/?convert={}'.format(curr.upper())
    ).content.decode())[0]['price_{}'.format(curr.lower())])
    return wish_btc * btc_to_curr
'''

@memoize_timeout(10*60)
def convert(fsym, tsyms):
    allowed = {'WISH', 'USD', 'ETH', 'EUR', 'BTC'}
    assert(fsym in allowed and not (set(tsyms.split(',')) - allowed))
    print(fsym, tsyms)
    return json.loads(requests.get(
        'https://min-api.cryptocompare.com/data/price?fsym={fsym}&tsyms={tsyms}'.format(fsym=fsym, tsyms=tsyms)
    ).content.decode())


def to_wish(curr, amount=1):
    return amount * (convert(curr, 'WISH')['WISH'])

