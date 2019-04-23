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
            # print('cache')
            if time.time() - v[1] > self.timeout:
                # print('updating')
                v = self.cache[key] = f(*args, **kwargs), time.time()
            return v[0]
        return func


@memoize_timeout(10*60)
def convert(fsym, tsyms):
    eosish_factor = 1.0
    revesre_convert = False
    allowed = {'WISH', 'USD', 'ETH', 'EUR', 'BTC', 'NEO', 'EOS', 'EOSISH', 'BNB', 'TRX', 'TRONISH', 'USDT'}
    if fsym == 'EOSISH' or tsyms == 'EOSISH':
        eosish_factor = float(
        requests.get('https://api.chaince.com/tickers/eosisheos/',
                     headers={'accept-version': 'v1'}).json()['price']
        )
        print('eosish factor', eosish_factor, flush=True)
        if fsym == 'EOSISH':
            fsym = 'EOS'
            if tsyms == fsym:
                return {'EOS': eosish_factor}
        else:
            tsyms = 'EOS'
            if tsyms == fsym:
                return {'EOSISH': 1 / eosish_factor}
            revesre_convert = True
            eosish_factor = 1 / eosish_factor
    tronish = False
    if tsyms == 'TRONISH':
        if fsym == 'TRX':
            return {'TRONISH': 0.02}
        else:
            tsyms = 'TRX'
            tronish = True
    if fsym == 'TRONISH':
        fsym = 'TRX'
        answer = json.loads(requests.get(
            'http://127.0.0.1:5001/convert?fsym={fsym}&tsyms={tsyms}'.format(
                fsym=fsym, tsyms=tsyms)
        ).content.decode())
        answer[tsyms] = answer[tsyms] * 0.02
        return answer

    if fsym not in allowed or any([x not in allowed for x in tsyms.split(',')]):
        raise Exception('currency not allowed')
    print(fsym, tsyms)
    answer = json.loads(requests.get(
        'http://127.0.0.1:5001/convert?fsym={fsym}&tsyms={tsyms}'.format(fsym=fsym, tsyms=tsyms)
    ).content.decode())
    print('currency_proxi answer', answer, flush=True)
    if revesre_convert:
        answer = {'EOSISH': answer['EOS']}
        tsyms = 'EOSISH'
    answer[tsyms] = answer[tsyms] * eosish_factor
    if tronish:
        answer['TRONISH'] = answer['TRX'] * 0.02
    return answer


def to_wish(curr, amount=1):
    return amount * (convert(curr, 'WISH')['WISH'])
