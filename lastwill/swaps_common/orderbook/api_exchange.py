import datetime
import random
import string

from django.utils import timezone

from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ParseError, NotFound, ValidationError
from rest_framework.response import Response

from lastwill.contracts.submodels.common import send_in_queue
from lastwill.contracts.api_eos import get_user_for_token
from lastwill.swaps_common.orderbook.models import OrderBookSwaps
from lastwill.swaps_common.orderbook.api import get_swap_from_orderbook
from lastwill.settings import SWAPS_ORDERBOOK_QUEUE


@api_view(http_method_names=['POST'])
def create_swaps_order_api(request):
    if request.user.is_anonymous:
        raise PermissionDenied

    token = request.META['HTTP_TOKEN']

    exchange_account = get_user_for_token(token)

    base_coin_id = quote_coin_id = 0
    base_address = quote_address = None

    if 'base_coin_id' and 'quote_coin_id' in request.data:
        base_coin_id = request.data['base_coin_id']
        quote_coin_id = request.data['quote_coin_id']
    elif 'base_address' and 'quote_address' in request.data:
        base_address = request.data['base_address']
        quote_address = request.data['quote_address']
    else:
        raise ValidationError('Required pairs of: base_coin_id and quote_coin_id or base_address and quote_adress')

    if 'stop_date' in request.params:
        stop_date = datetime.datetime.strptime(request.data['stop_date'], '%Y-%m-%d %H:%M')
    else:
        stop_date = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=3)

    link = ''.join(
            random.choice(string.ascii_lowercase + string.digits) for _ in
            range(6)
        )

    memo = '0x' + ''.join(random.choice('abcdef' + string.digits) for _ in range(64))

    user_from_exchange = request.date['exchange_user_id']

    backend_contract = OrderBookSwaps(
            name='exchange_order',
            base_address=base_address,
            base_limit=None,
            base_coin_id=base_coin_id,
            quote_address=quote_address,
            quote_limit=None,
            quote_coin_id=quote_coin_id,
            owner_address=None,
            stop_date=stop_date,
            public=True,
            unique_link=link,
            user=exchange_account,
            broker_fee=False,
            memo_contract=memo,
            comment=None,
            min_base_wei=None,
            min_quote_wei=None,
            whitelist=False,
            base_amount_contributed=0,
            base_amount_total=0,
            quote_amount_contributed=0,
            quote_amount_total=0,
            is_exchange=True,
            exchange_user=user_from_exchange
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
    return Response(details)


