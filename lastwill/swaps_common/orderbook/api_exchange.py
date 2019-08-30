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
from lastwill.contracts.api_eos import get_user_for_token
from lastwill.swaps_common.orderbook.models import OrderBookSwaps
from lastwill.swaps_common.orderbook.api import get_swap_from_orderbook
from lastwill.swaps_common.tokentable.api import get_cmc_tokens
from lastwill.settings import SWAPS_ORDERBOOK_QUEUE, SECRET_KEY
from lastwill.profile.models import *


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

        try:
            payload = jwt.decode(session_token, SECRET_KEY)
            data = payload['data']
        except jwt.ExpiredSignatureError:
            return Response(data={'error': 'Expired signature'}, status=403, headers=session_token_headers)
        except jwt.InvalidTokenError:
            return Response(data={'error': 'Invalid token'}, status=403, headers=session_token_headers)

        exchange_domain_name = data['exchange_domain']
        exchange_account = User.objects.get(username=data['exchange_profile'])
        if exchange_account.username != exchange_domain_name:
            return Response(data={'error': 'Domain name not matching username'}, status=400, headers=session_token_headers)

        user_from_exchange = data['user']

        base_coin_id = quote_coin_id = 0
        base_address = quote_address = None

        if 'base_coin_id' and 'quote_coin_id' in request.data:
            base_coin_id = request.data['base_coin_id']
            quote_coin_id = request.data['quote_coin_id']
        elif 'base_address' and 'quote_address' in request.data:
            base_address = request.data['base_address']
            quote_address = request.data['quote_address']
        else:
            return Response(
                    data={'error': 'Required pairs of: base_coin_id and quote_coin_id or base_address and quote_adress'},
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
                base_address=base_address,
                base_limit=base_limit,
                base_coin_id=base_coin_id,
                quote_address=quote_address,
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

        if not(base_address and quote_address):
            backend_contract.contract_state = 'ACTIVE'
        else:
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
            api_key = request.META['HTTP_SESSION_TOKEN']
        except KeyError:
            return Response(data={'error': 'HTTP token not found'}, status=400,
                            headers=token_headers)

        user = get_user_for_token(api_key)

        exchange_user_id = request.data['user_id']
        exchange_domain = request.META['HTTP_ORIGIN']

        session_token = encode_session_token(exchange_domain, user.username, exchange_user_id, api_key)
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


def encode_session_token(domain, profile, user_id, api_key):
    now = datetime.datetime.utcnow()
    domain_name = urlparse(domain).netloc
    data = {
        'exchange_domain':  domain_name,
        'exchange_profile': profile,
        'user':             user_id,
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


def set_cors_headers(additional_header):
    return {
                'access-control-allow-methods': 'POST',
                'access-control-allow-headers': 'Content-Type, {header}'.format(header=additional_header),
                'access-control-allow-origin': '*',
                'vary': 'Origin, Access-Control-Request-Method, Access-Control-Request-Headers'

            }