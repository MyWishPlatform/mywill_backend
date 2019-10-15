import os
import django
import requests
from requests import Session, ConnectionError, Timeout, TooManyRedirects
import json
import time
from django.core.files.base import ContentFile
import math

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
django.setup()

from lastwill.swaps_common.tokentable.models import TokensCoinMarketCap
from django.core.mail import send_mail, EmailMessage
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

    # tokens_ids = ','.join(str(k) for k in key)
    # print(tokens_ids)
    # parameters = {
    #     'id': tokens_ids
    # }
    # rebuild to list values
    data = {'data': {}, 'price': {}}
    for token in tokens_ids:
        try:
            # print(response.text)
            data['data'].update(get_cmc_response(COINMARKETCAP_API_KEYS[0], {'id': token})['data'])
            data['price'].update(get_coin_price(COINMARKETCAP_API_KEYS[0], {'id': token, 'skip_invalid': True})['price'])

        except KeyError as e:
            print('API key reached limit. Using other API key.', e, flush=True)
            data['data'].update(get_cmc_response(COINMARKETCAP_API_KEYS[1], {'id': token})['data'])
            data['price'].update(get_coin_price(COINMARKETCAP_API_KEYS[1], {'id': token, 'skip_invalid': True})['price'])

    return data


def find_by_parameters():
    ids = first_request()
    id_from_market = [i for i in ids.keys()]

    result = id_from_market
    id_rank = {}
    for key, value in ids.items():
        if key in result:
            id_rank[key] = value
    #    print(id_rank)
    if len(id_rank) == 0:
        print('No new tokens', flush=True)
        return

    info_for_save = second_request(id_rank)
    rank = [i for i in id_rank.values()]
    count = 0

    # original_urls = []
    for key, value in info_for_save['data'].items():
        count = + 1

        token_platform = 'False'
        token_address = '0x0000000000000000000000000000000000000000'

        if value['platform'] is not None:
            token_platform = value['platform']['slug']
            token_address = value['platform']['token_address']

        # logo_url_mywish_base = 'https://github.com/MyWishPlatform/coinmarketcap_coin_images/raw/master'

        img_url = value['logo']
        # original_urls.append(logo_url)

        # split_url = logo_url.split('/')
        # img_name = split_url[7]
        img_name = img_url.split('/')[7]

        #print('original logo url is:', logo_url)
        # logo_mywish_url = os.path.join(logo_url_mywish_base, img_name)

        try:
            price = str(info_for_save['price'][str(value['id'])]['quote']['USD']['price'])
        except KeyError:
            price = None

        token_from_cmc = TokensCoinMarketCap.objects.filter(token_cmc_id=value['id']).first()
        if token_from_cmc:
            token_from_cmc.token_price = price
            token_from_cmc.token_rank = rank[count]
            token_from_cmc.save()

            print('token updated',
                  token_from_cmc.token_cmc_id,
                  token_from_cmc.token_short_name,
                  token_from_cmc.token_rank,
                  token_from_cmc.token_price,
                  flush=True
                  )
        else:
            token_from_cmc = TokensCoinMarketCap(
                token_cmc_id=value['id'],
                token_name=value['name'],
                token_short_name=value['symbol'],
                # image_link=logo_mywish_url,
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

    # url_list = " ".join(url for url in original_urls)

    # subj = """ CoimMarketCap tokens update: found new {c} tokens """.format(c=len(original_urls)),
    # mail = EmailMessage(
    #    subject=subj,
    #    body='',
    #    from_email=DEFAULT_FROM_EMAIL,
    #    to=[CMC_TOKEN_UPDATE_MAIL]
    # )
    # mail.send()


if __name__ == '__main__':
    while 1:
        print('token parsing start', flush=True)
        find_by_parameters()
        time.sleep(3600 * 24)
