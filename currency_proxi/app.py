import requests
import time
import json

from flask import Flask, request
from flask_restful import Resource, Api
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://lastwill_curr:lastwill_curr@localhost/lastwill_curr'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['USERNAME'] = 'lastwill_curr'
app.config['PASSWORD'] = 'lastwill_curr'
db = SQLAlchemy(app)


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


class CurrencyProxi(Resource):
    @memoize_timeout
    def get(self):
        req = request.get_json()
        fsym = req['fsym']
        tsyms = req['tsyms']
        allowed = {'WISH', 'USD', 'ETH', 'EUR', 'BTC', 'NEO'}
        if fsym not in allowed or any(
                [x not in allowed for x in tsyms.split(',')]):
            raise Exception('currency not allowed')
        print(fsym, tsyms)
        return json.loads(requests.get(
            'https://min-api.cryptocompare.com/data/price?fsym={fsym}&tsyms={tsyms}'.format(
                fsym=fsym, tsyms=tsyms)
        ).content.decode())


api = Api(app)
api.add_resource(CurrencyProxi, '/convert/')
