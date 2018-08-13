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


@memoize_timeout(10*60)
def convert(fsym, tsyms):
    allowed = {'WISH', 'USD', 'ETH', 'EUR', 'BTC', 'NEO', 'EOS'}
    if fsym not in allowed or any([x not in allowed for x in tsyms.split(',')]):
        raise Exception('currency not allowed')
    print(fsym, tsyms)
    return json.loads(requests.get(
        'http://127.0.0.1:5001/convert?fsym={fsym}&tsyms={tsyms}'.format(fsym=fsym, tsyms=tsyms)
    ).content.decode())


def to_wish(curr, amount=1):
    return amount * (convert(curr, 'WISH')['WISH'])
