from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response

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
        transaction_id = request.data.get("transaction_id")
        transactionFullInfo = get_status_by_id(transaction_id)

        if transactionFullInfo:
            request.data["updateTime"] = transactionFullInfo.get("updateTime")
            request.data["fromNetwork"] = transactionFullInfo.get("fromNetwork")
            request.data["toNetwork"] = transactionFullInfo.get("toNetwork")
            request.data["actualFromAmount"] = transactionFullInfo.get("actualFromAmount")
            request.data["actualToAmount"] = transactionFullInfo.get("actualToAmount")
            request.data["status"] = transactionFullInfo.get("status")
            request.data["walletFromAddress"] = transactionFullInfo.get("walletFromAddress")
            request.data["walletToAddress"] = transactionFullInfo.get("walletToAddress")
            request.data["walletDepositAddress"] = transactionFullInfo.get("walletDepositAddress")

        return self.create(request, *args, **kwargs)

    def get_queryset(self):
        walletAddress = self.request.query_params.get("walletAddress")
        return list(PanamaTransaction.objects.filter(walletFromAddress=walletAddress))

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        for _, token in enumerate(serializer.data):
            tokenInfo = TokensCoinMarketCap.objects \
                .filter(
                    token_short_name=token.get("ethSymbol")
                ) \
                .last()
            token["image_link"] = request.build_absolute_uri(
                tokenInfo.image.url
            )

        return Response(serializer.data)
