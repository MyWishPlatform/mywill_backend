import re
from decimal import Decimal

from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST

from .services import create_swap
from .status_request import get_status_by_id
from .models import PanamaTransaction
from lastwill.swaps_common.tokentable.models import CoinGeckoToken
from .serializers import UserTransactionSerializer


class UserTransactionsView(ListAPIView, CreateAPIView):
    """
    Basic view to create db entry about transaction and send list of user's transaction.
    method POST need to request transaction_id field(gives on frontend by binance API)
    method GET need to request walletAddress to response all user's transaction list
    """
    serializer_class = UserTransactionSerializer

    # get data from request and create new entry in db
    def post(self, request, *args, **kwargs):
        # types: panama, rbc_swap
        swap_type = request.data.get('type')

        if not swap_type:
            return Response(
                'Swap \'type\' field is required.',
                HTTP_400_BAD_REQUEST,
            )

        if swap_type == PanamaTransaction.SWAP_RBC:
            network = int(request.data['fromNetwork'])
            tx_id = request.data['transaction_id']
            from_amount = request.data['fromAmount']
            wallet_from_address = request.data['walletFromAddress']
            # response = create_swap(network, tx_hash)
            response = create_swap(
                from_network=network,
                tx_id=tx_id,
                from_amount=from_amount,
                wallet_address=wallet_from_address
            )

            return Response(*response)
        elif swap_type == PanamaTransaction.SWAP_PANAMA:
            try:
                transaction_id = request.data.get("transaction_id")
            except KeyError:
                return Response(
                    data='No wallet address has been passed.',
                    status=HTTP_400_BAD_REQUEST
                )

            if PanamaTransaction.objects.filter(transaction_id=transaction_id).exists():
                return Response(
                    data='This transaction has been exists in database.',
                    status=HTTP_400_BAD_REQUEST
                )

            transactionFullInfo = get_status_by_id(transaction_id)

            if transactionFullInfo:
                request.data["updateTime"] = transactionFullInfo.get("updateTime")
                request.data["type"] = PanamaTransaction.SWAP_PANAMA
                request.data["fromNetwork"] = transactionFullInfo.get("fromNetwork")
                request.data["toNetwork"] = transactionFullInfo.get("toNetwork")
                request.data["actualFromAmount"] = transactionFullInfo.get("actualFromAmount")
                request.data["actualToAmount"] = transactionFullInfo.get("actualToAmount")
                request.data["status"] = transactionFullInfo.get("status")
                request.data["walletFromAddress"] = transactionFullInfo.get("walletFromAddress").lower()
                request.data["walletToAddress"] = transactionFullInfo.get("walletToAddress").lower()
                request.data["walletDepositAddress"] = transactionFullInfo.get("walletDepositAddress").lower()

            return self.create(request, *args, **kwargs)

        return Response(
            'Invalid swap type.',
            HTTP_400_BAD_REQUEST,
        )
    def get_queryset(self):
        wallet_address = self.request.query_params.get("walletAddress")

        if not wallet_address:
            return []

        return list(PanamaTransaction.objects.filter(wallet_from_address=wallet_address.lower()))

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        for _, token in enumerate(serializer.data):
            # add token image link to response
            tokenInfo = CoinGeckoToken.objects \
                        .filter(
                            short_title__iexact=token.get("ethSymbol")
                        ) \
                        .last()

            # magic_code - start
            if token.get("status") == "Cancelled":
                token['code'] = 0  # red
            elif token.get("status") == "Completed":
                token["code"] = 2  # green
            else:
                token["code"] = 1  # yellow

            token["status"] = re.sub(
                r"(\w)([A-Z])", r"\1 \2",
                token.get("status")
            ).capitalize()

            if tokenInfo is None:
                tokenInfo=CoinGeckoToken.objects \
                          .filter(
                              short_title__iexact=token.get("bscSymbol")
                          ) \
                          .last()
            if tokenInfo is None:
                token["image_link"] = 'https://raw.githubusercontent.com/MyWishPlatform/etherscan_top_tokens_images/master/fa-empire.png'
            else:
                token["image_link"] = request.build_absolute_uri(
                    tokenInfo.image_file.url
                )
            # token["actualFromAmount"] = str(
            #     Decimal(token.get("actualFromAmount")).normalize()
            # )
            # token["actualToAmount"] = str(
            #     Decimal(token.get("actualToAmount")).normalize()
            # )
            token["actualFromAmount"] = str(float(token["actualFromAmount"]))
            token["actualToAmount"] = str(float(token["actualToAmount"]))
            # magic_code - finish

        return Response(serializer.data)
