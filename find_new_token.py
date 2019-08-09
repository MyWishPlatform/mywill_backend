import os
import django
import requests
from requests import Session, ConnectionError, Timeout, TooManyRedirects
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lastwill.settings')
django.setup()

from lastwill.swaps_common.tokentable.models import TokensCoinMarketCap
from django.core.mail import send_mail, EmailMessage
from lastwill.settings import DEFAULT_FROM_EMAIL, CMC_TOKEN_UPDATE_MAIL


def first_request():
    res = requests.get('https://s2.coinmarketcap.com/generated/search/quick_search.json')
    l = res.json()
    id_rank = {}
    for i in range(len(l)):
        id_rank[(l[i]['id'])] =l[i]['rank']
    return id_rank


def second_request(token_list):
    key = [key[0] for key in token_list.items()]
    tokens_ids = ','.join(str(k) for k in key)
    # print(tokens_ids)
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info'
    parameters = {
        'id': tokens_ids
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': 'f66f6d8d-742d-4ba7-af33-e61a55c7c135',
    }
    # rebuild to list values
    session = Session()
    session.headers.update(headers)
    try:
        response = session.get(url, params=parameters)
        # print(response.text)
        data = json.loads(response.text)
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)
    return data


def find_by_parameters():
    db = TokensCoinMarketCap.objects.all().values_list('token_cmc_id', flat=True)
    # convert to list
    ids = first_request()
    id_from_market = [i for i in ids.keys()]
    id_from_db = [id for id in db]
    if len(list(id_from_market)) != len(id_from_db):
        result = list(set(id_from_market)-set(id_from_db))
        id_rank = {}
        for key,value in ids.items():
            if key in result:
                id_rank[key] = value
#    print(id_rank)
    info_for_save = second_request(id_rank)
    rank = [value for i in id_rank.values()]
    count = 0

    original_urls = []
    for key, value in info_for_save['data'].items():
        count =+ 1

        token_platform = None
        token_address = '0x0000000000000000000000000000000000000000'

        if value['platform'] is not None:
            token_platform = value['platform']['slug']
            token_address = value['platform']['token_address']

        logo_url_mywish_base = 'https://github.com/MyWishPlatform/coinmarketcap_coin_images/raw/master'

        logo_url = value['logo']
        original_urls.append(logo_url)

        split_url = logo_url.split('/')
        img_name = split_url[7]

        logo_mywish_url = os.path.join(logo_url_mywish_base, img_name)

        print('saving token to db',
              value['id'], value['name'], value['symbol'], logo_mywish_url,
              rank[count], token_platform, token_address,
              flush=True)
        print('original logo url is:', logo_url)

        token_from_cmc = TokensCoinMarketCap(
                token_cmc_id=value['id'],
                token_name=value['name'],
                token_short_name=value['symbol'],
                image_link=logo_mywish_url,
                token_rank=rank[count],
                token_platform=token_platform,
                token_address=token_address
        )

#        token_from_cmc.save()

    url_list = " ".join(url for url in original_urls)

    subj = """CoimMarketCap tokens update: found new {c}tokens""".format(c=len(url_list)),
    mail = EmailMessage(
        subject=subj,
        body="""
        {urls}
        """.format(urls=url_list),
        from_email=DEFAULT_FROM_EMAIL,
        to=CMC_TOKEN_UPDATE_MAIL
    )
    mail.send()


if __name__ == '__main__':
    find_by_parameters()
