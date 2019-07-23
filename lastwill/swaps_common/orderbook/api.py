import datetime
import random
import string

from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.response import Response

from lastwill.contracts.serializers import ContractDetailsSWAPS2Serializer
from lastwill.contracts.submodels.common import Contract
from lastwill.contracts.submodels.swaps import ContractDetailsSWAPS2
from lastwill.swaps_common.orderbook.models import OrderBookSwaps


def get_swap_from_orderbook(swap_id):
    backend_contract = OrderBookSwaps.objects.filter(id=swap_id).first()
    saved_details = {
        'id': backend_contract.id,
        'name': backend_contract.name,
        'base_address': backend_contract.base_address,
        'base_limit': backend_contract.base_limit,
        'base_coin_id': backend_contract.base_coin_id,
        'quote_address': backend_contract.quote_address,
        'quote_limit': backend_contract.quote_limit,
        'quote_coin_id': backend_contract.quote_coin_id,
        'owner_address': backend_contract.owner_address,
        'stop_date': backend_contract.stop_date,
        'memo_contract': backend_contract.memo_contract,
        'unique_link': backend_contract.unique_link,
        'state': backend_contract.state,
        'public': backend_contract.public,
        'broker_fee': backend_contract.broker_fee,
        'broker_fee_address': backend_contract.broker_fee_address,
        'broker_fee_base': backend_contract.broker_fee_base,
        'broker_fee_quote': backend_contract.broker_fee_quote
    }
    return saved_details


@api_view(http_method_names=['POST'])
def create_contract_swaps_backend(request):
    if request.user.is_anonymous:
        raise PermissionDenied

    contract_details = request.data

    base_address = contract_details['base_address'] if 'base_address' in contract_details else ""
    quote_address = contract_details['quote_address'] if 'quote_address' in contract_details else ""
    owner_address = contract_details['owner_address'] if 'owner_address' in contract_details else ""
    contract_name = contract_details['name'] if 'name' in contract_details else ""
    stop_date_conv = datetime.datetime.strptime(contract_details['stop_date'], '%Y-%m-%d %H:%M')
    base_coin_id_param = contract_details['base_coin_id'] if 'base_coin_id' in contract_details else 0
    quote_coin_id_param = contract_details['quote_coin_id'] if 'quote_coin_id' in contract_details else 0

    broker_fee = contract_details['broker_fee'] if 'broker_fee' in contract_details else False

    link = ''.join(
            random.choice(string.ascii_lowercase + string.digits) for _ in
            range(6)
        )

    backend_contract = OrderBookSwaps(
            name=contract_name,
            base_address=base_address,
            base_limit=contract_details['base_limit'],
            base_coin_id=base_coin_id_param,
            quote_address=quote_address,
            quote_limit=contract_details['quote_limit'],
            quote_coin_id=quote_coin_id_param,
            owner_address=owner_address,
            stop_date=stop_date_conv,
            public=contract_details['public'],
            unique_link=link,
            user=request.user,
            broker_fee=broker_fee,
    )

    if broker_fee:
        if 'broker_fee_address' in contract_details:
            backend_contract.broker_fee_address = contract_details['broker_fee']
        if 'broker_fee_base' in contract_details:
            backend_contract.broker_fee_base = contract_details['broker_fee_base']
        if 'broker_fee_quote' in contract_details:
            backend_contract.broker_fee_quote = contract_details['broker_fee_quote']

    backend_contract.save()
    fake_swap = create_swap2_for_events(backend_contract)
    print(fake_swap, flush=True)

    #backend_contract.memo_contract = fake_swap.memo_contract

    if base_address or quote_address:
        backend_contract.state = 'WAITING_FOR_ACTIVATION'
        fake_swap = create_swap2_for_events(backend_contract)
        print(fake_swap, flush=True)
    else:
        backend_contract.state = 'ACTIVE'

    backend_contract.save()
    details = get_swap_from_orderbook(swap_id=backend_contract.id)

    return Response(details)


def create_swap2_for_events(order):

    order_details = get_swap_from_orderbook(order.id)

    swap2_contract = Contract(
            contract_type=21,
            cost=0,
            user=order.user,
            name=order_details['name'],
            state='CREATED'
    )
    excluded_fields = ['name', 'id', 'state', 'base_coin_id','quote_coin_id']
    swap2_params = {k:v for k,v in order_details.items() if k not in excluded_fields}
    swap2_params['order_id'] = order_details['id']
    swap2_contract.save()
    swap2_details = ContractDetailsSWAPS2Serializer().create(swap2_contract, swap2_params)
    swap2_contract.state = 'WAITING_FOR_ACTIVATION'
    swap2_contract.save()
    order.state = 'ACTIVE'
    order.memo_contract = swap2_details.memo_contract
    order.save()

    return swap2_contract.id


def add_swap2_state(order_id):
    swap_contract = ContractDetailsSWAPS2.objects.filter(order_id=order_id).first()
    return swap_contract.contract_id


@api_view(http_method_names=['GET'])
def show_contract_swaps_backend(request):
    if request.user.is_anonymous:
        raise PermissionDenied

    swap_id = request.query_params.get('swap_id', None)
    if swap_id is not None:
        details = get_swap_from_orderbook(swap_id=swap_id)
        if details['base_address'] or details['quote_address']:
            details['contract_state'] = add_swap2_state(swap_id)
        else:
            details['contract_state'] = ""
        return Response(details)
    else:
        raise ParseError


@api_view(http_method_names=['GET'])
def show_user_contract_swaps_backend(request):
    if request.user.is_anonymous:
        raise PermissionDenied

    orders_list = []
    orders = OrderBookSwaps.objects.filter(user=request.user)
    for order in orders:
        details = get_swap_from_orderbook(swap_id=order.id)
        orders_list.append(details)

    return Response(orders_list)


@api_view(http_method_names=['POST'])
def edit_contract_swaps_backend(request, swap_id):
    if request.user.is_anonymous:
        raise PermissionDenied

    if swap_id is None:
        raise ParseError

    swap_order = OrderBookSwaps.objects.filter(id=swap_id).first()

    if request.user != swap_order.user:
        if not request.user.profile.is_swaps_admin:
            raise PermissionDenied

    params = request.data

    if 'name' in params:
        swap_order.name = params['name']
    if 'stop_date' in params:
        stop_date = datetime.datetime.strptime(params['stop_date'], '%Y-%m-%d %H:%M')
        swap_order.stop_date = stop_date
    if 'base_address' in params:
        swap_order.base_address = params['base_address']
    if 'base_limit' in params:
        swap_order.base_limit = params['base_limit']
    if 'base_coin_id' in params:
        swap_order.base_coin_id = params['base_coin_id']
    if 'quote_address' in params:
        swap_order.quote_address = params['quote_address']
    if 'quote_limit' in params:
        swap_order.quote_limit = params['quote_limit']
    if 'quote_coin_id' in params:
        swap_order.quote_coin_id = params['quote_coin_id']
    if 'owner_address' in params:
        swap_order.owner_address = params['owner_address']
    if 'owner_address' in params:
        swap_order.public = params['public']
    if 'broker_fee' in params:
        swap_order.broker_fee = params['broker_fee']
    if params['broker_fee']:
        if 'broker_fee_address' in params:
            swap_order.broker_fee_address = params['broker_fee']
        if 'broker_fee_base' in params:
            swap_order.broker_fee_base = params['broker_fee_base']
        if 'broker_fee_quote' in params:
            swap_order.broker_fee_quote = params['broker_fee_quote']

    swap_order.save()
    details = get_swap_from_orderbook(swap_id=swap_order.id)

    return Response(details)


@api_view(http_method_names=['GET'])
def get_swap_v3_for_unique_link(request):
    link = request.query_params.get('unique_link', None)
    if not link:
        raise PermissionDenied
    swaps_order = OrderBookSwaps.objects.filter(unique_link=link).first()
    if not swaps_order:
        raise PermissionDenied

    details = get_swap_from_orderbook(swaps_order.id)
    if details['base_address'] or details['quote_address']:
        details['contract_state'] = add_swap2_state(swaps_order.id)
    else:
        details['contract_state'] = ""
    return Response(details)


@api_view(http_method_names=['GET'])
def get_swap_v3_public(request):
    backend_contracts = OrderBookSwaps.objects.filter(public=True)

    res = []
    for order in backend_contracts:
        res.append(get_swap_from_orderbook(order.id))

    return Response(res)
