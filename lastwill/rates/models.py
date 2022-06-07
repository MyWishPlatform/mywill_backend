import requests
from django.db import models

from lastwill.settings import (COINGECKO_API_URL, COINGECKO_SYMBOLS, TEMP_SYMBOLS)


class RateException(Exception):
    pass


class Rate(models.Model):
    fsym = models.CharField(max_length=50)
    tsym = models.CharField(max_length=50)
    value = models.FloatField()
    is_up_24h = models.BooleanField()
    last_update_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('fsym', 'tsym'),)

    def __str__(self):
        return f"{self.fsym}-{self.tsym}"

    @classmethod
    def _get_coin_info(cls, sym):
        coin_id = cls._get_coingecko_sym(sym)
        response = requests.get(COINGECKO_API_URL.format(coin_id=coin_id))
        if response.status_code != 200:
            raise RateException('Cannot get token info from coingecko.com')

        return response.json()

    @staticmethod
    def _get_coingecko_sym(sym):
        try:
            return COINGECKO_SYMBOLS[sym]
        except KeyError:
            raise RateException(f'Unknown symbol: {sym}')

    @classmethod
    def _process_rate(cls, fsym, tsym):
        if fsym == tsym:
            return 1.0, False

        fsym_info = cls._get_coin_info(fsym)['market_data']

        try:
            value = fsym_info['current_price'][tsym.lower()]
            is_up_24h = fsym_info['price_change_24h_in_currency'][tsym.lower()] > 0

        except KeyError:
            tsym_info = cls._get_coin_info(tsym)['market_data']

            fsym_usd_rate = fsym_info['current_price']['usd']
            tsym_usd_rate = tsym_info['current_price']['usd']
            value = fsym_usd_rate / tsym_usd_rate
            is_up_24h = fsym_info['price_change_24h_in_currency']['usd'] > 0

        return value, is_up_24h

    def _get_result_value(self, value):
        if self.fsym == self.tsym:
            return 1.0
        if self.fsym == 'TRONISH':
            return value * 0.02
        elif self.tsym == 'TRONISH':
            return value / 0.02
        elif 'EOSISH' in (self.fsym, self.tsym):
            markets = requests.get('https://alcor.exchange/api/markets').json()
            for market in markets:
                if market['quote_token']['symbol']['name'] == 'EOSISH':
                    if self.fsym == 'EOSISH':
                        return value * market['last_price']
                    else:
                        return value / market['last_price']
            raise Exception('Cannot get EOSISH rate')
        else:
            return value

    def update(self):
        # check if we need replace symbol for additional rate logic
        fsym = self.fsym if self.fsym not in TEMP_SYMBOLS else TEMP_SYMBOLS[self.fsym]
        tsym = self.tsym if self.tsym not in TEMP_SYMBOLS else TEMP_SYMBOLS[self.tsym]

        raw_value, is_up_24h = self._process_rate(fsym, tsym)

        self.value = self._get_result_value(raw_value)  # apply additional logic if required
        self.is_up_24h = is_up_24h
