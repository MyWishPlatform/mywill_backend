import json
import time

import requests
from binance.client import Client

from lastwill.settings import BINANCE_PAYMENT_ADDRESS, BINANCE_PAYMENT_PASSWORD


class ConvertationFetchError(Exception):
    pass


class memoize_timeout:
    def __init__(self, timeout):
        self.timeout = timeout
        self.cache = {}

    def __call__(self, f):
        def func(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            v = self.cache.get(key, (0, 0))
            # print('cache')
            if time.time() - v[1] > self.timeout:
                # print('updating')
                v = self.cache[key] = f(*args, **kwargs), time.time()
            return v[0]

        return func


@memoize_timeout(10 * 60)
def convert(fsym, tsyms):
    for convert_attempt in range(5):
        try:
            answer = Converter.try_convert(fsym, tsyms) or convert_symbols(fsym, tsyms)
            if tsyms not in answer:
                print('failed to fetch convertible sum, retrying', flush=True)
                print('answer', answer, flush=True)
                raise ConvertationFetchError
            else:
                break
        except ConvertationFetchError:
            pass
    else:
        raise Exception('cannot fetch cost for 5 attempts')

    return answer


class Converter:
    USD = "USD"
    ETH = "ETH"
    EOS = "EOS"
    main_curr = [USD, ETH, EOS]

    convert_dict = {
        "SWAP": {
            "id": "swaps-network",
            "compare_curr": ETH
        },
        "OKB": {
            "id": "okb",
            "compare_curr": ETH
        },
        "WISH": {
            "id": "wish",
            "compare_curr": ETH
        },
    }

    allowed = [k for k in convert_dict.keys()] + [i for i in main_curr]

    @classmethod
    def try_convert(cls, fsym, tsym):
        """
        Placeholder until old converter doesn't removed.
        Try to convert currencies, return false on error.
        """
        try:
            answer = cls.process(fsym, tsym)
        except Exception as e:
            return False
        return answer

    @classmethod
    def process(cls, fsym, tsym):
        if fsym == tsym:
            return {tsym: 1.0}

        for s in fsym, tsym:
            if s not in cls.allowed:
                raise Exception('currency not allowed')

        ref_curr = cls.get_ref(fsym, tsym)
        r0 = cls._get_rates(fsym, ref_curr)
        r1 = cls._get_rates(tsym, ref_curr)

        return {tsym: 1 / r1 * r0}

    @classmethod
    def get_ref(cls, fsym, tsym):
        main_curr = [i for i in (fsym, tsym) if i in cls.main_curr]
        main_curr_len = len(main_curr)

        if main_curr_len == 2:
            return 'USD'
        elif main_curr_len == 1:
            return main_curr[0]
        else:
            return cls.convert_dict[fsym]['compare_curr']


    @classmethod
    def _get_rates(cls, curr, ref_curr='usd'):
        if curr == ref_curr:
            return 1.0

        _id = cls.convert_dict[curr]['id']
        ref_curr = ref_curr.lower()

        if curr == 'WISH':
            return cls._get_wish_rates(ref_curr)

        return float(
            requests.get(
                'https://api.coingecko.com/api/v3/simple/price?ids={}&vs_currencies={}'.format(
                    _id, ref_curr
                )).json()[_id][ref_curr]
        )

    @classmethod
    def _get_wish_rates(cls, ref_curr):
        wish_factor = float(
            requests.get('https://api.coingecko.com/api/v3/exchanges/binance_dex/tickers?coin_ids=mywish')
            .json()['tickers'][0]['converted_last'][ref_curr]
            )
        return wish_factor


def convert_symbols(fsym, tsyms):
    eosish_factor = swap_factor = okb_factor = wish_factor = 1.0
    reverse_convert_eos = reverse_convert_swap = reverse_convert_okb = reverse_convert_wish = False
    allowed = {'WISH', 'USD', 'ETH', 'EUR', 'BTC', 'NEO', 'EOS', 'EOSISH', 'BNB', 'TRX', 'TRONISH', 'USDT', 'WAVES',
               'SWAP', 'OKB'}
    if fsym == 'EOSISH' or tsyms == 'EOSISH':
        eosish_factor = float(
            requests.get('https://api.coingecko.com/api/v3/simple/price?ids=eosish&vs_currencies=eos')
            .json()['eosish']['eos']
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
            reverse_convert_eos = True
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
    if fsym == 'SWAP' or tsyms == 'SWAP':
        swap_factor = float(
            requests.get('https://api.coingecko.com/api/v3/simple/price?ids=swaps-network&vs_currencies=eth')
            .json()['swaps-network']['eth']
            )
        print('swap factor', swap_factor, flush=True)
        if fsym == 'SWAP':
            fsym = 'ETH'
            if tsyms == fsym:
                return {'ETH': swap_factor}
        else:
            tsyms = 'ETH'
            if tsyms == fsym:
                return {'SWAP': 1 / swap_factor}
            reverse_convert_swap = True
            swap_factor = 1 / swap_factor
    if fsym == 'OKB' or tsyms == 'OKB':
        okb_factor = float(
            requests.get('https://api.coingecko.com/api/v3/simple/price?ids=okb&vs_currencies=eth')
            .json()['okb']['eth']
            )
        print('okb factor', okb_factor, flush=True)
        if fsym == 'OKB':
            fsym = 'ETH'
            if tsyms == fsym:
                return {'ETH': okb_factor}
        else:
            tsyms = 'ETH'
            if tsyms == fsym:
                return {'OKB': 1 / okb_factor}
            reverse_convert_okb = True
            okb_factor = 1 / okb_factor
    if fsym == 'WISH' or tsyms == 'WISH':
        wish_factor = float(
            requests.get('https://api.coingecko.com/api/v3/exchanges/binance_dex/tickers?coin_ids=mywish')
            .json()['tickers'][0]['converted_last']['eth']
            )
        print('wish factor', wish_factor, flush=True)
        if fsym == 'WISH':
            fsym = 'ETH'
            if tsyms == fsym:
                return {'ETH': wish_factor}
        else:
            tsyms = 'ETH'
            if tsyms == fsym:
                return {'WISH': 1 / wish_factor}
            reverse_convert_wish = True
            wish_factor = 1 / wish_factor

    if fsym not in allowed or any([x not in allowed for x in tsyms.split(',')]):
        raise Exception('currency not allowed')
    # print(fsym, tsyms)
    answer = json.loads(requests.get(
        'http://127.0.0.1:5001/convert?fsym={fsym}&tsyms={tsyms}'.format(fsym=fsym, tsyms=tsyms)
    ).content.decode())
    # print('currency_proxi answer', answer, flush=True)
    if reverse_convert_eos:
        answer = {'EOSISH': answer['EOS']}
        tsyms = 'EOSISH'
    if reverse_convert_swap:
        answer = {'SWAP': answer['ETH']}
        tsyms = 'SWAP'
    if reverse_convert_okb:
        answer = {'OKB': answer['ETH']}
        tsyms = 'OKB'
    if reverse_convert_wish:
        answer = {'WISH': answer['ETH']}
        tsyms = 'WISH'
    if eosish_factor != 1.0:
        answer[tsyms] = answer[tsyms] * eosish_factor
    if swap_factor != 1.0:
        answer[tsyms] = answer[tsyms] * swap_factor
    if okb_factor != 1.0:
        answer[tsyms] = answer[tsyms] * okb_factor
    if wish_factor != 1.0:
        answer[tsyms] = answer[tsyms] * wish_factor
    if tronish:
        answer['TRONISH'] = answer['TRX'] / 0.02
    return answer


def to_wish(curr, amount=1):
    return amount * (convert(curr, 'WISH')['WISH'])


def swap_to_wish(amount=1):
    return amount * to_wish('SWAP', amount)


def bnb_to_wish():
    client = Client(BINANCE_PAYMENT_ADDRESS, BINANCE_PAYMENT_PASSWORD)
    client.API_URL = 'https://dex.binance.org/api'
    wish_price = client.get_ticker(symbol='WISH-2D5_BNB')[0]['lastPrice']
    return 1 / float(wish_price)
