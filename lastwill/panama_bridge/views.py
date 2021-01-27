import re

from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST

from .status_request import get_status_by_id
from .models import PanamaTransaction
from lastwill.swaps_common.tokentable.models import TokensCoinMarketCap
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
        try:
            transaction_id = request.data.get("transaction_id")
        except KeyError:
            return Response(
                data='No wallet address from Cookie.',
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
            request.data["fromNetwork"] = transactionFullInfo.get("fromNetwork")
            request.data["toNetwork"] = transactionFullInfo.get("toNetwork")
            request.data["actualFromAmount"] = transactionFullInfo.get("actualFromAmount")
            request.data["actualToAmount"] = transactionFullInfo.get("actualToAmount")
            request.data["status"] = transactionFullInfo.get("status")
            request.data["walletFromAddress"] = transactionFullInfo.get("walletFromAddress").lower()
            request.data["walletToAddress"] = transactionFullInfo.get("walletToAddress").lower()
            request.data["walletDepositAddress"] = transactionFullInfo.get("walletDepositAddress").lower()

        return self.create(request, *args, **kwargs)

    def get_queryset(self):
        walletAddress = self.request.query_params.get("walletAddress").lower()
        return list(PanamaTransaction.objects.filter(walletFromAddress=walletAddress))

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        for _, token in enumerate(serializer.data):
            # add token image link to response
            tokenInfo = TokensCoinMarketCap.objects \
                .filter(
                    token_short_name=token.get("ethSymbol")
                ) \
                .last()

            # magic_code - start
            if token.get("status") == "Cancelled":
                token['code'] = 0  # red
            elif token.get("status") == "Completed":
                token["code"] = 2  # green
            else:
                token["code"] = 1  # yellow
            # magic_code - finish

            token["status"] = re.sub(
                r"(\w)([A-Z])", r"\1 \2",
                token.get("status")
            ).capitalize()
            token["image_link"] = request.build_absolute_uri(
                tokenInfo.image.url
            )

        return Response(serializer.data)
