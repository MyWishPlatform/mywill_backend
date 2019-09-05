import datetime
import random
import string
import jwt
from urllib.parse import urlparse

from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt

from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ParseError, NotFound, ValidationError
from rest_framework.response import Response

from lastwill.contracts.submodels.common import send_in_queue
#from lastwill.contracts.api_eos import get_user_for_token
from lastwill.swaps_common.orderbook.models import OrderBookSwaps
from lastwill.swaps_common.orderbook.api import get_swap_from_orderbook
from lastwill.swaps_common.tokentable.api import get_cmc_tokens
from lastwill.settings import SWAPS_ORDERBOOK_QUEUE, SECRET_KEY, SWAPS_WIDGET_HOST, SWAPS_WIDGET_TOKEN
from lastwill.profile.models import *


def encode_session_token(domain, profile, user_id, api_token):
    now = datetime.datetime.utcnow()

    data = {
        'exchange_domain':  domain,
        'exchange_profile': profile,
        'user':             user_id,
        'api_token':        api_token
    }
    payload = {
        'exp': now + datetime.timedelta(days=0, seconds=10),
        'iat': now,
        'data': data
    }
    return jwt.encode(
            payload,
            SECRET_KEY,
            algorithm='HS256'
    )


def decode_payload(domain_name, payload_token, error_headers):
    try:
        payload = jwt.decode(payload_token, SECRET_KEY)
        data = payload['data']
    except jwt.ExpiredSignatureError:
        return Response(data={'error': 'Expired signature'}, status=403, headers=error_headers)
    except jwt.InvalidTokenError:
        return Response(data={'error': 'Invalid token'}, status=403, headers=error_headers)

    original_domain_name = data['exchange_domain']
    #exchange_account = User.objects.get(username=data['exchange_profile'])
    current_domain_name = domain_name

    if original_domain_name != current_domain_name:
        return Response(data={'error': 'Domain name not matching original'}, status=400, headers=error_headers)

    return data


def get_exchange_for_token(token, domain, error_headers):
    api_token = APIToken.objects.filter(token=token, swaps_exchange_domain=domain)
    if not api_token:
        return Response(data={'error': 'Token does not exist'}, status=404, headers=error_headers)
    api_token = api_token.first()
    if not api_token.active:
        return Response(data={'error': 'Your token is not active'}, status=404, headers=error_headers)

    return {
        'user': api_token.user,
        'api_token': api_token
    }


def set_cors_headers(additional_header):
    return {
                'access-control-allow-methods': 'POST',
                'access-control-allow-headers': 'Content-Type, {header}'.format(header=additional_header),
                'access-control-allow-origin': '*',
                'vary': 'Origin, Access-Control-Request-Method, Access-Control-Request-Headers'

            }


def get_domain(request):
    return urlparse(request.META['HTTP_ORIGIN']).netloc


@xframe_options_exempt
@api_view(http_method_names=['POST', 'OPTIONS'])
def create_swaps_order_api(request):
    session_token_headers = set_cors_headers('SESSION-TOKEN')
    if request.method == 'OPTIONS':
        return Response(status=200, headers=session_token_headers)
    else:
        try:
            session_token = request.META['HTTP_SESSION_TOKEN']
        except KeyError:
            return Response(data={'error': 'Session token not found'}, status=400,
                            headers=session_token_headers)

        host = get_domain(request)
        data = decode_payload(host, session_token, session_token_headers)
        if isinstance(data, Response):
            return data

        exchange_account = User.objects.get(username=data['exchange_profile'])
        user_from_exchange = data['user']

        base_coin_id = quote_coin_id = 0
        base_address = quote_address = None

        if 'base_coin_id' and 'quote_coin_id' in request.data:
            base_coin_id = request.data['base_coin_id']
            quote_coin_id = request.data['quote_coin_id']
        else:
            return Response(
                    data={'error': 'Required pair of base_coin_id and quote_coin_id'},
                    status=400,
                    headers=session_token_headers
            )

        order_name = request.data['name']
        base_limit = request.data['base_limit']
        quote_limit = request.data['quote_limit']

        stop_date = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=3)

        link = ''.join(
                random.choice(string.ascii_lowercase + string.digits) for _ in
                range(6)
            )

        memo = '0x' + ''.join(random.choice('abcdef' + string.digits) for _ in range(64))

        backend_contract = OrderBookSwaps(
                name=order_name,
                base_address="",
                base_limit=base_limit,
                base_coin_id=base_coin_id,
                quote_address="",
                quote_limit=quote_limit,
                quote_coin_id=quote_coin_id,
                owner_address=None,
                stop_date=stop_date,
                public=True,
                unique_link=link,
                user=exchange_account,
                broker_fee=False,
                memo_contract=memo,
                comment='',
                min_base_wei=None,
                min_quote_wei=None,
                whitelist=False,
                whitelist_address=None,
                base_amount_contributed=0,
                base_amount_total=0,
                quote_amount_contributed=0,
                quote_amount_total=0,
                is_exchange=True,
                exchange_user=user_from_exchange,
        )

        backend_contract.save()

        backend_contract.state = 'ACTIVE'
        backend_contract.contract_state = 'CREATED'

        backend_contract.save()
        details = get_swap_from_orderbook(swap_id=backend_contract.id)

        print('sending swap order in queue ', backend_contract.id, flush=True)
        send_in_queue(backend_contract.id, 'launch', SWAPS_ORDERBOOK_QUEUE)
        return Response(details, status=200, headers=session_token_headers)


@xframe_options_exempt
@api_view(http_method_names=['POST', 'OPTIONS'])
def create_token_for_session(request):
    token_headers = set_cors_headers('TOKEN')
    if request.method == 'OPTIONS':
        return Response(status=200, headers=token_headers)
    else:
        try:
            api_key = request.META['HTTP_TOKEN']
        except KeyError:
            return Response(data={'error': 'HTTP token not found'}, status=400,
                            headers=token_headers)

        exchange_domain = get_domain(request)

        exchange_data = get_exchange_for_token(api_key, exchange_domain, token_headers)
        if isinstance(exchange_data, Response):
            return exchange_data

        exchange_user_id = request.data['user_id']
        user = exchange_data['user']
        api_token = exchange_data['api_token']


        session_token = encode_session_token(exchange_domain, user.username, exchange_user_id, api_token.token)
        data = {'session_token': session_token}
        return Response(
                data=data,
                status=200,
                headers=token_headers
        )


@api_view(http_method_names=['GET', 'OPTIONS'])
def get_cmc_tokens_for_api(request):
    list_headers = set_cors_headers('SESSION-TOKEN')

    if request.method == 'OPTIONS':
        return Response(status=200, headers=list_headers)
    else:
        try:
            session_token = request.META['HTTP_SESSION_TOKEN']
        except KeyError:
            return Response(data={'error': 'Session token not found'}, status=400,
                            headers=list_headers)

        tokens = get_cmc_tokens()
        return Response(data=tokens, status=200, headers=list_headers)


@api_view(http_method_names=['GET', 'OPTIONS'])
def get_user_orders_for_api(request):
    orderlist_headers = set_cors_headers('SESSION-TOKEN')

    if request.method == 'OPTIONS':
        return Response(status=200, headers=orderlist_headers)
    else:
        try:
            session_token = request.META['HTTP_SESSION_TOKEN']
        except KeyError:
            return Response(data={'error': 'Session token not found'}, status=400,
                            headers=orderlist_headers)

        host = get_domain(request)
        data = decode_payload(host, session_token, orderlist_headers)
        if isinstance(data, Response):
            return data

        exchange_account = User.objects.get(username=data['exchange_profile'])
        user_from_exchange = data['user']

        orderlist = []
        orders = OrderBookSwaps.objects.filter(user=exchange_account, exchange_user=user_from_exchange)
        for order in orders:
            details = get_swap_from_orderbook(swap_id=order.id)
            if details['state'] != 'HIDDEN':
                orderlist.append(details)

        return Response(data=orderlist, status=200, headers=orderlist_headers)


@api_view(http_method_names=['POST', 'OPTIONS'])
def delete_order_for_user(request):
    cors_headers = set_cors_headers('SESSION-TOKEN')

    if request.method == 'OPTIONS':
        return Response(status=200, headers=cors_headers)
    else:
        try:
            session_token = request.META['HTTP_SESSION_TOKEN']
        except KeyError:
            return Response(data={'error': 'Session token not found'}, status=400, headers=cors_headers)

        host = get_domain(request)
        data = decode_payload(host, session_token, cors_headers)
        if isinstance(data, Response):
            return data

        user_from_exchange = data['user']

        if 'order_id' in request.data:
            order_id = request.data['order_id']
        else:
            return Response(data={'error': 'order_id is required'}, status=400, headers=cors_headers)

        swaps_order = OrderBookSwaps.objects.filter(id=order_id)

        if not swaps_order:
            return Response(data={'error': 'order with this id does not exist'}, status=404, headers=cors_headers)

        swaps_order = swaps_order.first()

        if not swaps_order.exchange_user == user_from_exchange:
            return Response(data={'error': 'user in request and user saves in order does not match'},
                            status=403,
                            headers=cors_headers)

        swaps_order.exchange_user = None
        swaps_order.save()

        return Response(
                data={'status': 'deleted ok'},
                status=200,
                headers=cors_headers
        )


@api_view(http_method_names=['POST', 'OPTIONS'])
def create_token_for_session_mywish(request):
    if request.user.is_anonymous:
        raise PermissionDenied

    api_token = APIToken.objects.filter(token=SWAPS_WIDGET_TOKEN, swaps_exchange_domain=SWAPS_WIDGET_HOST).first()

    mywish_username = api_token.user.username

    session_token = encode_session_token(SWAPS_WIDGET_HOST, mywish_username, request.user.id, SWAPS_WIDGET_TOKEN)
    data = {'session_token': session_token}

    return Response(data=data)
