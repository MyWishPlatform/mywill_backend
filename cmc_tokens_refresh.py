import os
import datetime
import django
import requests
from requests import Session, ConnectionError, Timeout, TooManyRedirects
import json
import time
from django.core.files.base import ContentFile
from django.utils import timezone
import math

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
django.setup()

from lastwill.swaps_common.tokentable.models import TokensCoinMarketCap, TokensUpdateTime
from lastwill.settings import DEFAULT_FROM_EMAIL, CMC_TOKEN_UPDATE_MAIL, COINMARKETCAP_API_KEYS


def first_request():
    res = requests.get('https://s2.coinmarketcap.com/generated/search/quick_search.json')
    l = res.json()
    id_rank = {}
    for i in range(len(l)):
        id_rank[(l[i]['id'])] = l[i]['rank']
    return id_rank


def get_cmc_response(api_key, parameters):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info'
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    session = Session()
    session.headers.update(headers)
    response = session.get(url, params=parameters)
    return json.loads(response.text)


def get_coin_price(api_key, parameters):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    session = Session()
    session.headers.update(headers)
    response = session.get(url, params=parameters)
    data = {'price': json.loads(response.text)['data']}
    return data


def second_request(token_list):
    key = [key[0] for key in token_list.items()]
    count = math.ceil(len(key) / 500)
    tokens_ids = []
    for i in range(1, count + 1):
        tokens_ids.append(','.join(str(k) for k in key[(i - 1) * 500:i * 500]))

    data = {'data': {}, 'price': {}}
    for token in tokens_ids:
        try:
            data['data'].update(get_cmc_response(COINMARKETCAP_API_KEYS[0], {'id': token})['data'])
            data['price'].update(get_coin_price(COINMARKETCAP_API_KEYS[0], {'id': token, 'skip_invalid': True})['price'])

        except KeyError as e:
            print('API key reached limit. Using other API key.', e, flush=True)
            data['data'].update(get_cmc_response(COINMARKETCAP_API_KEYS[1], {'id': token})['data'])
            data['price'].update(get_coin_price(COINMARKETCAP_API_KEYS[1], {'id': token, 'skip_invalid': True})['price'])

    return data


def find_by_parameters(current_time, checker_object):
    id_rank = first_request()

    info_for_save = second_request(id_rank)
    rank = [i for i in id_rank.values()]
    count = 0

    for key, value in info_for_save['data'].items():
        count += 1
        if count >= len(rank):
            break

        token_platform = None
        token_address = '0x0000000000000000000000000000000000000000'

        if value['platform'] is not None:
            token_platform = value['platform']['slug']
            token_address = value['platform']['token_address']

        img_url = value['logo']
        img_name = img_url.split('/')[7]

        try:
            price = str(info_for_save['price'][str(value['id'])]['quote']['USD']['price'])
        except KeyError:
            price = None

        token_from_cmc = TokensCoinMarketCap.objects.filter(token_cmc_id=value['id']).first()
        if token_from_cmc:
            if price is not None and token_from_cmc.token_price != price:
                token_from_cmc.token_price = price

            new_rank = id_rank[int(value['id'])]
            if token_from_cmc.token_rank != new_rank:
                token_from_cmc.token_rank = new_rank

            token_from_cmc.save()

            print('token updated',
                  token_from_cmc.token_cmc_id,
                  token_from_cmc.token_short_name.encode('utf-8'),
                  token_from_cmc.token_rank,
                  token_from_cmc.token_price,
                  flush=True
                  )
        else:
            token_from_cmc = TokensCoinMarketCap(
                token_cmc_id=value['id'],
                token_name=value['name'],
                token_short_name=value['symbol'],
                token_rank=rank[count],
                token_platform=token_platform,
                token_address=token_address,
                token_price=price
            )

            token_from_cmc.image.save(name=img_name, content=ContentFile(requests.get(img_url).content))
            token_from_cmc.save()

            print('saved token',
                  token_from_cmc.token_cmc_id,
                  token_from_cmc.token_name.encode('utf-8'),
                  token_from_cmc.token_short_name.encode('utf-8'),
                  token_from_cmc.image.name,
                  token_from_cmc.token_rank,
                  token_from_cmc.token_platform,
                  token_from_cmc.token_address.encode('utf-8'),
                  token_from_cmc.token_price,
                  flush=True
                  )
    checker_object.last_time_updated = current_time
    checker_object.save()
    print('update done, time is %s ' % current_time, flush=True)


if __name__ == '__main__':
    while 1:
        print('preparing to update token list', flush=True)
        now = datetime.datetime.now(timezone.utc)
        previous_check = TokensUpdateTime.objects.all().first()
        if now > previous_check.last_time_updated + datetime.timedelta(hours=23):
            print('token parsing start', flush=True)
            find_by_parameters(now, previous_check)
        else:
            print('last check was %s, skipping' % previous_check.last_time_updated, flush=True)

        time.sleep(3600 * 24)
