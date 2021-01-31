"""
    Модуль-парсер данных об актуальных токенах, полученных из GoinGecko.

    Этапы синхронизации с базой данных токенов CoinGecko.
    - В CoinGecko запрашиваются список всех актуальных токенов.
    - В CoinGecko запрашивается данные котировок по всем токенам.
    - Полученные данные форматируются в соответствии с форматом, заданным моделью CionGeckoToken.
    - Из базы данных запрашиваются все записи о токенами. Записи сравниваются с полученным списком по полям токенов title и short title.
        - Если о токене есть НЕ скрытая запись в БД и его нет в списке актуальных токенов, то запись скрывается.
        - Если о токене есть скрытая запись в БД и он есть в списке актуальных токнов, то запись НЕ скрывается.
        !!! ОГРАНИЧЕНИЯ РЕАЛИЗАЦИИ !!!
        - В статистике CoinGecko нет данных о платформе и адресе токена, которые позволили бы со 100% точностью их идентифицировать, поэтому при создании токенов используется проверка на совместную уникальность полей title и short_title. В качестве предлагаемого варианта: запрашивать данные на etherscan'е.
    - Из базы данных запрашиваются только НЕ скрытые записи о токенах.
        - Если токена нет в результате запроса в БД, то создается новая запись с этим токеном.
        - Если токен есть в результате запроса в БД, то данные о токене обновляются в БД.
    - Подгружаются иконки к каждому НЕ скрытому токену. По-умолчанию в качестве иконки токену устанавливается fa-empire.png.

"""
from requests import get
from time import sleep

from django.core.files.base import ContentFile

from lastwill.swaps_common.tokentable.models import (
    CoinGeckoToken,
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


def get_coingecko_token_id(exclude_token=['thorecoin', ]):
    """
    Возвращает список идентификаторов крипто-токенов из CoinGecko.com.

    ---

    Возвращаемое значение:
    - Перечень идентификаторов (str) : list.
    """
    target_url = 'https://api.coingecko.com/api/v3/coins/list'
    response = get(target_url).json()
    coingecko_id_list = [item.get('id') for item in response]

    if exclude_token:
        for token in exclude_token:
            coingecko_id_list.pop(coingecko_id_list.index(token))

    return coingecko_id_list


def get_token_market_data_from_coingecko(start=0, stop_slice=300, timeout=5):
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

            result += response
            start = stop_slice
            stop_slice += 300

            sleep(timeout)

            continue
        else:
            params.update({
                'ids': ','.join(id_list[start:]),
            })
            result += push_request_to_coingecko(target_url, params)

        break

    # print(len(id_list), len(result))

    return result


def format_marketdata():
    """
    Фильтрует и форматирует данные для сохранения в базу данных.

    ---

    Возвращаемое значение - dict.

    Формат возвращаемого значения:
    {
        <token_ticker>:
        {
            <token_title> as string,
            <token_short_title> as string,
            <token_image_link> as string,
            <token_rank> as integer,
            <token_usd_price> as float
        },
        ...
    }
    """
    # Пример данных:
    # [
    #     {
    #         "id": "1337", -
    #         "symbol": "1337", as short name
    #         "name": "Elite", as repr name
    #         "image": "https://assets.coingecko.com/coins/images/686/large/EliteLogo256.png?1559143523", as image link
    #         "current_price": 0.00001408, as token price
    #         "market_cap": 415426, -
    #         "market_cap_rank": 1247, as token rank
    #         "fully_diluted_valuation": null, -
    #         "total_volume": 5.26, -
    #         "high_24h": 0.0000185, -
    #         "low_24h": 0.00001542, -
    #         "price_change_24h": -0.00000274, -
    #         "price_change_percentage_24h": -16.31284, -
    #         "market_cap_change_24h": -80975.61992168, -
    #         "market_cap_change_percentage_24h": -16.31252, -
    #         "circulating_supply": 29515041222.0315, -
    #         "total_supply": null, -
    #         "max_supply": null, -
    #         "ath": 0.00108002, -
    #         "ath_change_percentage": -98.69678, -
    #         "ath_date": "2018-01-09T00:00:00.000Z", -
    #         "atl": 2.2e-7, -
    #         "atl_change_percentage": 6281.09, -
    #         "atl_date": "2020-06-26T11:53:55.843Z", -
    #         "roi": null, -
    #         "last_updated": "2020-12-04T14:12:07.411Z" -
    #     },
    # ]
    token_market_data = get_token_market_data_from_coingecko(timeout=0)
    result = {}

    try:
        for _, item in enumerate(token_market_data):
            prepared_token_data = {
                'token_title': item.get('name'),
                'token_short_title': item.get('symbol'),
                'token_image_link': item.get('image'),
                'token_rank': item.get('market_cap_rank'),
                'token_usd_price': item.get('current_price'),
            }
            result.update(
                {
                    prepared_token_data.get('token_short_title'): prepared_token_data
                }
            )
    except (TypeError, Exception) as exception_error:
        print(
            'Error in format_marketdata: {}'.format(exception_error)
        )
        return 0

    return result


def get_all_coingecko_tokens():
    """
    Возвращает объект QuerySet со всеми CoinGecko токенами.
    """
    return CoinGeckoToken.objects.all()


def get_current_coingecko_tokens():
    """
    Возвращает объект QuerySet со всеми актуальными CoinGecko токенами
    (is_displayed=True).
    """
    return CoinGeckoToken.objects.all().filter(is_displayed=True)


def get_actual_coingecko_token_list(actual_tokens: dict) -> list:
    """
    Возвращает список кортежей в формате
    [(<token_title>, <token_short_title>), ...].

    ---

    Принимаемые параметры:
    - Список токенов : dict

    ---

    Возвращаемое значение:
    - Список кортежей : list(tuple(), ...)
    """
    if not actual_tokens:
        return 0

    actual_token_list = []

    try:
        for _, actual_token in enumerate(actual_tokens):
            current_token = (
                actual_tokens.get(actual_token).get('token_title'),
                actual_tokens.get(actual_token).get('token_short_title'),
            )
            actual_token_list.append(current_token)
    except (KeyError, Exception) as exception_error:
        print(
            'Error in get_actual_coingecko_token_list: {}.'.format(
                exception_error
            )
        )
        return 0

    return actual_token_list


def refresh_token_visibility(actual_coingecko_token_list: list):
    """
    Обновляет видимость CoinGecko токенов в базе данных.

    ---

    Принимаемые параметры:
    - Список токенов coingecko_short_titles : list

    ---

    Возвращаемое значение:
    - ...

    """
    if not actual_coingecko_token_list:
        return 0

    current_tokens = get_all_coingecko_tokens()
    current_tokens.update(is_displayed=True)

    print(len(current_tokens))

    # TODO: Подумать над реализацией. Не рационально отправлять 6К+ запросов
    # в БД. Нужно собрать записи, которые не попали по фильру и одним запросом
    # обновить им поле is_displayed на False.
    for _, token in enumerate(current_tokens):
        if not (
            token.title,
            token.short_title
        ) in actual_coingecko_token_list:
            # token.update(is_displayed=False)
            current_tokens.filter(
                title=token.title,
                short_title=token.short_title
            ).update(is_displayed=False)

    print(len(current_tokens))

    return 1


def sync_data_with_db():
    """
    Записывает и сохраняет полученые данные в базу данных.
    """
    data_for_sync = format_marketdata()

    actual_tokens = get_actual_coingecko_token_list(data_for_sync)

    if not refresh_token_visibility(actual_tokens):
        return 0

    actual_cg_tokens = get_current_coingecko_tokens()

    print(
        f'Total coingecko tokens has been founded: {len(data_for_sync)}.'
    )

    counter = 0
    # TODO: Продумать вариант с сохранением объектов порционно, а не всем
    # перечнем (6К+ записей на 4.12.2020).
    try:
        for _, actual_token in enumerate(actual_tokens):
            counter += 1
            token_title = actual_token[0]
            token_short_title = actual_token[1]
            cg_token = actual_cg_tokens.filter(
                title=token_title,
                short_title=token_short_title
            )

            if not cg_token.exists():
                token = data_for_sync.get(token_short_title)
                token_rank = token.get('token_rank')
                token_usd_price = token.get('token_usd_price')

                if not token_rank and not token_usd_price:
                    CoinGeckoToken.objects.create(
                        title=token.get('token_title'),
                        short_title=token.get('token_short_title'),
                        source_image_link=token.get('token_image_link'),
                    )
                elif not token_rank and token_usd_price:
                    CoinGeckoToken.objects.create(
                        title=token.get('token_title'),
                        short_title=token.get('token_short_title'),
                        source_image_link=token.get('token_image_link'),
                        usd_price=token.get('token_usd_price'),
                    )
                elif token_rank and not token_usd_price:
                    CoinGeckoToken.objects.create(
                        title=token.get('token_title'),
                        short_title=token.get('token_short_title'),
                        source_image_link=token.get('token_image_link'),
                        rank=token.get('token_rank'),
                    )
                else:
                    CoinGeckoToken.objects.create(
                        title=token.get('token_title'),
                        short_title=token.get('token_short_title'),
                        source_image_link=token.get('token_image_link'),
                        rank=token.get('token_rank'),
                        usd_price=token.get('token_usd_price'),
                    )

                print(
                    '{}. Token "{} ({})" has been added successfully.'.format(
                        counter,
                        token.get('token_title'),
                        token.get('token_short_title'),
                    )
                )
            else:
                token = data_for_sync.get(token_short_title)
                token_rank = token.get('token_rank')
                token_usd_price = token.get('token_usd_price')

                if not token_rank and not token_usd_price:
                    cg_token.update(
                        source_image_link=token.get('token_image_link'),
                    )
                elif not token_rank and token_usd_price:
                    cg_token.update(
                        source_image_link=token.get('token_image_link'),
                        usd_price=token_usd_price,
                    )
                elif token_rank and not token_usd_price:
                    cg_token.update(
                        source_image_link=token.get('token_image_link'),
                        usd_price=token_usd_price,
                    )
                else:
                    cg_token.update(
                        source_image_link=token.get('token_image_link'),
                        rank=token_rank,
                        usd_price=token_usd_price,
                    )

                print(
                    '{}. Token "{} ({})" has been updated successfully.'.format(
                        counter,
                        token.get('token_title'),
                        token.get('token_short_title'),
                    )
                )
    except (TypeError, Exception) as exception_error:
        print(
            'Error in sync_data_with_db: {}'.format(exception_error)
        )
        return 0

    print(
        'Total tokens has been refreshed: {}.\nToken market data has been synced at {}.'.format(
            counter,
            get_current_coingecko_tokens().last().updated_at
        )
    )

    return 1


def add_icon_to_token(token_queryset=get_current_coingecko_tokens(), timeout=0):
    """
        Скачивает и добавляет иконку токену.
    """
    counter = 0
    for token in token_queryset:
        counter += 1
        icon_url = token.source_image_link
        icon_name = icon_url.split('/')[-1] \
                            .split('?')[0]

        if token.image_file.url.split('/')[-1] == 'fa-empire.png' and not icon_url == 'missing_large.png':
            token.image_file.save(
                name='cg_logo_{0}_{1}'.format(
                    token.short_title,
                    icon_name
                ),
                content=ContentFile(get(icon_url).content)
            )

        print(
            f'{counter}. Token "{token.short_title}" icon has been added successfully.'
        )

        if timeout:
            sleep(timeout)

    return 1
