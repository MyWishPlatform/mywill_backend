from django_filters.rest_framework.backends import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED, HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from lastwill.settings import RUBIC_EXC_URL
from lastwill.swaps_common.mailing.models import SwapsNotificationDefaults
from lastwill.swaps_common.orderbook.models import OrderBookSwaps
from lastwill.swaps_common.orderbook.serializers import \
     OrderBookSwapsModelSerializer


class OrderBookSwapsModelViewSet(ModelViewSet):
    queryset = OrderBookSwaps.objects.all()
    serializer_class = OrderBookSwapsModelSerializer
    filter_backends = [DjangoFilterBackend,]
    filterset_fields = [
        'network',
        'contract_address',
        'user',
        'public',
        'state',
    ]

    def get_permissions(self):
        if self.action in [
            'create_order',
        ]:
            return [IsAuthenticated(),]

        return [AllowAny(),]

    def create_order(self, request):
        """
            Возвращает созданную сделку.

            ---

            Возвращаемое значение:
            - Response(data=<data>, status=<http_status_code>)
        """
        # ! ---
        # if request.user.is_anonymous:
        #     raise PermissionDenied

        # contract_details = request.data

        # base_address = contract_details['base_address'] if 'base_address' in contract_details else ""
        # quote_address = contract_details['quote_address'] if 'quote_address' in contract_details else ""
        # owner_address = contract_details['owner_address'] if 'owner_address' in contract_details else ""
        # contract_name = contract_details['name'] if 'name' in contract_details else ""
        # network_id = contract_details.get('network', 1)
        # stop_date_conv = datetime.datetime.strptime(contract_details['stop_date'], '%Y-%m-%d %H:%M')
        # base_coin_id_param = contract_details['base_coin_id'] if 'base_coin_id' in contract_details else 0
        # quote_coin_id_param = contract_details['quote_coin_id'] if 'quote_coin_id' in contract_details else 0

        # broker_fee = contract_details['broker_fee'] if 'broker_fee' in contract_details else False
        # comment = contract_details['comment'] if 'comment' in contract_details else ""

        # link = ''.join(
        #         random.choice(string.ascii_lowercase + string.digits) for _ in
        #         range(6)
        #     )

        # memo = '0x' + ''.join(random.choice('abcdef' + string.digits) for _ in range(64))

        # min_base_wei = contract_details['min_base_wei'] if 'min_base_wei' in contract_details else ""
        # min_quote_wei = contract_details['min_quote_wei'] if 'min_quote_wei' in contract_details else ""
        # whitelist = contract_details['whitelist'] if 'whitelist' in contract_details else False
        # notification = contract_details['notification'] if 'notification' in contract_details else None

        # notification_email = None
        # notification_tg = None
        # if notification:
        #     if not ('notification_email' in contract_details or 'notification_tg' in contract_details):
        #         raise ParseError('notificaion_email or notification_tg must be passed')

        #     notification_defaults = request.user.swapsnotificationdefaults_set.all()
        #     if not notification_defaults:
        #         notification_defaults = SwapsNotificationDefaults(user=request.user)
        #     else:
        #         notification_defaults = notification_defaults.first()

        #     notification_defaults.notification = notification

        #     if 'notification_email' in contract_details:
        #         notification_email = contract_details['notification_email']
        #         notification_defaults.email = notification_email
        #     if 'notification_tg' in contract_details:
        #         notification_tg = contract_details['notification_tg']
        #         notification_defaults.telegram_name = notification_tg

        #     notification_defaults.save()

        # backend_contract = OrderBookSwaps(
        #         name=contract_name,
        #         network_id=network_id,
        #         base_address=base_address.lower(),
        #         base_limit=contract_details['base_limit'],
        #         base_coin_id=base_coin_id_param,
        #         quote_address=quote_address.lower(),
        #         quote_limit=contract_details['quote_limit'],
        #         quote_coin_id=quote_coin_id_param,
        #         owner_address=owner_address.lower(),
        #         stop_date=stop_date_conv,
        #         public=contract_details['public'],
        #         unique_link=link,
        #         user=request.user,
        #         broker_fee=broker_fee,
        #         memo_contract=memo,
        #         comment=comment,
        #         min_base_wei=min_base_wei,
        #         min_quote_wei=min_quote_wei,
        #         whitelist=whitelist,
        #         base_amount_contributed=0,
        #         base_amount_total=0,
        #         quote_amount_contributed=0,
        #         quote_amount_total=0,
        #         notification_email=notification_email,
        #         notification_telegram_name=notification_tg,
        #         notification=notification
        # )

        # if broker_fee:
        #     backend_contract.broker_fee = contract_details['broker_fee']
        #     if 'broker_fee_address' in contract_details:
        #         backend_contract.broker_fee_address = contract_details['broker_fee_address'].lower()
        #     if 'broker_fee_base' in contract_details:
        #         backend_contract.broker_fee_base = contract_details['broker_fee_base']
        #     if 'broker_fee_quote' in contract_details:
        #         backend_contract.broker_fee_quote = contract_details['broker_fee_quote']

        # if whitelist:
        #     backend_contract.whitelist_address = contract_details['whitelist_address']

        # if request.META['HTTP_HOST'] == RUBIC_EXC_URL:
        #     backend_contract.is_rubic_order = True

        # backend_contract.state = 'ACTIVE'
        # backend_contract.contract_state = 'CREATED'
        # backend_contract.save()

        # details = get_swap_from_orderbook(swap_id=backend_contract.id)
        # print('sending swap order in queue ', backend_contract.id, flush=True)
        # send_in_queue(backend_contract.id, 'launch', SWAPS_ORDERBOOK_QUEUE)
        # return Response(details)
        # ---

        new_contract = request.data.copy()

        user=request.user,
        notification = new_contract.get('notification')

        if request.META['HTTP_HOST'] == RUBIC_EXC_URL:
            new_contract.update({'is_rubic_order': True, })

        if notification:
            notification_email = new_contract.get('notification_email')
            notification_tg = new_contract.get('notification_tg')

            if not notification_email or not notification_tg:
                return _get_response_object(
                    message='Notificaion email or notification tg must be passed.',
                    status_code=HTTP_400_BAD_REQUEST
                )

            noti_defaults = user.swapsnotificationdefaults_set.all()

            if not noti_defaults:
                noti_defaults = SwapsNotificationDefaults(user=user)
            else:
                noti_defaults = noti_defaults.first()

            noti_defaults.notification = notification
            noti_defaults.email = new_contract.get('notification_email')
            noti_defaults.telegram_name = new_contract.get('notification_tg')

            noti_defaults.save()

        deserialized_data = self.get_serializer(data=new_contract)

        if not deserialized_data.is_valid():
            return _get_response_object(
                message=deserialized_data.errors,
                status_code=HTTP_400_BAD_REQUEST
            )

        self.perform_create(deserialized_data)

        return _get_response_object(
            message=deserialized_data.data,
            status_code=HTTP_201_CREATED
        )

    def get_orders(self, request):
        """
            Возвращает список сделок.

            ---

            Возвращаемое значение:
            - Response(data=<data>, status=<http_status_code>)
        """
        # ! ---
        # is_rubic = False
        # rubic_initialized = False
        # if request.META['HTTP_HOST'] == RUBIC_EXC_URL:
        #     is_rubic = True
        #     rubic_initialized = True

        # backend_contracts = OrderBookSwaps.objects.filter(
        #     public=True,
        #     is_rubic_order=is_rubic,
        #     rubic_initialized=rubic_initialized
        # ).order_by('state_changed_at')

        # res = []
        # for order in backend_contracts:
        #     if order.state != 'EXPIRED' and order.state == 'ACTIVE':
        #         res.append(get_swap_from_orderbook(order.id))

        # return Response(res)
        # ---

        source_host = request.META.get('HTTP_HOST')

        if source_host != RUBIC_EXC_URL:
            is_rubic_order = False
            rubic_initialized = False
        else:
            is_rubic_order = True
            rubic_initialized = True

        orders = self.filter_queryset(self.get_queryset()) \
                        .filter(
                            is_rubic_order=is_rubic_order,
                            rubic_initialized=rubic_initialized,
                        ) \
                        .order_by('state_changed_at')

        if not orders.exists():
            return _get_response_object(
                message='No orders has been founded.',
                status_code=HTTP_404_NOT_FOUND
            )

        serialized_data = self.get_serializer(orders, many=True)

        return _get_response_object(
            message={
                'count': len(serialized_data.data),
                'data': serialized_data.data,
            },
            status_code=HTTP_200_OK
        )


def _get_response_object(message, status_code:int=HTTP_200_OK):
    """
        Возвращает объект Response c передаваемыми параметрами.

        ---

        Входные параметры:
        - message : any
        - status_code : int, по-умолчанию HTTP_200_OK
    """
    return Response(
        data=message,
        status=status_code
    )
