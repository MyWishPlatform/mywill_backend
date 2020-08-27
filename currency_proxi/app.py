import requests
import time
import json

from flask import Flask, request
from flask_restful import Resource, Api

from lastwill.settings_local import CRYTOCOMPARE_API_KEY

app = Flask(__name__)


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
                print('updating')
                v = self.cache[key] = f(*args, **kwargs), time.time()
            return v[0]
        return func


class CurrencyProxi(Resource):
    @memoize_timeout(10*60)
    def get(self):
        # req = request.get_json()
        fsym = request.args.get('fsym')
        tsyms = request.args.get('tsyms')
        return json.loads(requests.get(
            'https://min-api.cryptocompare.com/data/price?fsym={fsym}&tsyms={tsyms}&api_key={apikey}'.format(
                fsym=fsym, tsyms=tsyms, apikey=CRYPTOCOMPARE_API_KEY)
        ).content.decode())


api = Api(app)
api.add_resource(CurrencyProxi, '/convert')
