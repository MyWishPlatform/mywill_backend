import requests
from requests import Session, ConnectionError, Timeout, TooManyRedirects
import json
from lastwill.swaps_common.tokentable.models import TokensCoinMarketCap


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
        print(response.text)
        data = json.loads(response.text)
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)
    return data


def find_by_parameters():
    db = TokensCoinMarketCap.objects.all().values_list('token_cmc_id', flat=True)
    # convert to list
    ids = first_request()
    id_from_market = [i for i in ids.keys()]
    id_from_db = [id for id in db ]
    if len(list(id_from_market)) != len(id_from_db):
        result = list(set(id_from_market)-set(id_from_db))
        id_rank ={}
        for key,value in ids.items():
            if key in  result:
                id_rank[key] = value
    print(id_rank)
    info_for_save = second_request(id_rank)
    rank = [value for i in id_rank.values()]
    count = 0

    for key, value in info_for_save['data'].items():
        count += 1
        if value['platform'] is not None:
            obj = TokensCoinMarketCap(token_cmc_id=value['id'], token_name=value['name'],
                                      token_short_name=value['symbol'], image_link=value['logo'],
                                      token_rank=rank[count], token_platform=value['platform']['slug'],
                                      token_address=value['platform']['token_address'])
 #           obj.save()

        else:
            obj = TokensCoinMarketCap(token_cmc_id=value ['id'], token_name=value['name'],
                                      token_short_name=value['symbol'], image_link=value['logo'],
                                      token_rank=rank[count], token_platform=None,
                                      token_address='0x0000000000000000000000000000000000000000')
#            obj.save()


if __name__ == '__main__':
    find_by_parameters()
