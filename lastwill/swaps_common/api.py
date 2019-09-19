
from rest_framework.response import Response
from django.core.paginator import Paginator

from lastwill.swaps_common.models import UnifiedSwapsTable
from lastwill.contracts.submodels.common import Contract
from lastwill.swaps_common.orderbook.models import OrderBookSwaps
from lastwill.swaps_common.orderbook.api import get_swap_from_orderbook


def get_non_active_orders(request):
    p = request.query_params.get('p', 1)
    try:
        p = int(p)
    except ValueError:
        p = 1

    exclude_states = ['ACTIVE', 'HIDDEN']
    order_list = OrderBookSwaps.objects.all().exclude(state__in=exclude_states).order_by('created_date')
    swaps_list = UnifiedSwapsTable.objects.all().exclude(order_oject__state__in=exclude_states, details_objects__contract__state__in=exclude_states)

    paginator = Paginator(swaps_list, 100)
    orders = paginator.page(p)
    res = []
    for row in orders:
        res.append(get_swap_from_orderbook(row.id))

    return Response({
        'total': paginator.count,
        'pages': paginator.num_pages,
        'list': res
    })