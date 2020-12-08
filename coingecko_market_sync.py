"""
    Добавляет в базу данных новые данные о всех токенах, имеющиеся в GoinGecko.
"""
from requests import Session, get

from lastwill.swaps_common.tokentable.models import (
    Tokens,
    TokensCoinMarketCap,
    TokensUpdateTime
)


def push_request_to_coingecko(url, params=None):
    """
    Отправляет запрос с идентификаторами токенов в CoinGecko.com

    ---

    Входные параметры:
    - tokens : tuple, list.

    ---

    Возвращаемое значение:
    - Распарсенный JSON : list.
    """
    response = get(url, params)

    return response.json()


def get_coingecko_token_id():
    """
    Возвращает список идентификаторов крипто-токенов из CoinGecko.com.

    ---

    Возвращаемое значение:
    - Перечень идентификаторов (str) : list.
    """
    target_url = 'https://api.coingecko.com/api/v3/coins/list'
    response = get(target_url).json()
    coingecko_id_list = [item['id'] for item in response]

    coingecko_id_list.pop(
        coingecko_id_list.index('thorecoin')
    )

    return coingecko_id_list


def get_token_market_data_from_coingecko(start=0, stop_slice=300):
    """

    """
    id_list = get_coingecko_token_id()
    target_url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
    }
    result = []

    while 1:
        # Здесь происходит "магия", не обращайте внимания.
        #
        # Запросы отправляются несколько раз по 300 идентификаторов,
        # ответ записывается в результирующий список.
        if stop_slice < len(id_list):
            params.update({
                'ids': ','.join(id_list[start:stop_slice]),
            })
            response = push_request_to_coingecko(target_url, params)

            if 'error' in response:
                raise Exception(
                    f'\nSending the request has been failed!\nError message: "{response["error"]}".'
                )

            result += push_request_to_coingecko(target_url, params)
            start = stop_slice
            stop_slice += 300

            continue
        else:
            params.update({
                'ids': ','.join(id_list[start:]),
            })
            result += push_request_to_coingecko(target_url, params)

        break

    # print(len(id_list), len(result))

    return result


def prepare_data_for_sync_with_db():
    """
    Фильтрует данные для сохранения в базу данных.

    ---

    Пример данных:
    [
        {
            "id": "1337", -
            "symbol": "1337", as short name
            "name": "Elite", as repr name
            "image": "https://assets.coingecko.com/coins/images/686/large/EliteLogo256.png?1559143523", as image link
            "current_price": 0.00001408, as token price
            "market_cap": 415426, -
            "market_cap_rank": 1247, as token rank
            "fully_diluted_valuation": null, -
            "total_volume": 5.26, -
            "high_24h": 0.0000185, -
            "low_24h": 0.00001542, -
            "price_change_24h": -0.00000274, -
            "price_change_percentage_24h": -16.31284, -
            "market_cap_change_24h": -80975.61992168, -
            "market_cap_change_percentage_24h": -16.31252, -
            "circulating_supply": 29515041222.0315, -
            "total_supply": null, -
            "max_supply": null, -
            "ath": 0.00108002, -
            "ath_change_percentage": -98.69678, -
            "ath_date": "2018-01-09T00:00:00.000Z", -
            "atl": 2.2e-7, -
            "atl_change_percentage": 6281.09, -
            "atl_date": "2020-06-26T11:53:55.843Z", -
            "roi": null, -
            "last_updated": "2020-12-04T14:12:07.411Z" -
        },
    ]
    """
    token_market_data = get_token_market_data_from_coingecko()

    result = []

    for _, item in enumerate(token_market_data):
        prepared_token_data = {
            'token_name': item['name'],
            'token_short_name': item['symbol'],
            'image_link': item['image'],
            'token_rank': item['market_cap_rank'],
            'token_price': item['current_price'],
        }

        result.append(prepared_token_data)

    return result


def sync_data_with_db():
    """
    Записывает и сохраняет полученые данные в базу данных.
    """
    data_for_sync = prepare_data_for_sync_with_db()

    # Продумать вариант с сохранением объектов порционно, а не всем
    # перечнем (6К записей на 4.12.2020).
    try:
        sync_transaction = TokensCoinMarketCap.objects.bulk_create(
            [
                TokensCoinMarketCap(
                    token_cmc_id=0,
                    token_name=item['token_name'],
                    token_short_name=item['token_short_name'],
                    token_platform='',
                    token_address='0x0000000000000000000000000000000000000000',
                    image_link=item['image_link'],
                    token_rank=item['token_rank'],
                    token_price=item['token_price']
                ) for _, item in enumerate(data_for_sync)
            ]
        )
    except TypeError as exception_error:
        raise Exception(exception_error)
    except:
        raise Exception('Something went wrong!')

    sync_update = TokensUpdateTime.objects.create()
    sync_update.save()

    print(f'Tokens has been add: {len(data_for_sync)}.\nToken market data has beed synced at {sync_update.last_time_updated}.')

    return 0
