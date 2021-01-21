from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response

from status_request import get_status_by_id
from panama_bridge.models import PanamaTransaction
from panama_bridge.serializers import UserTransactionSerializer


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
            request.data["symbol"] = transactionFullInfo.get("symbol")
            request.data["status"] = transactionFullInfo.get("status")
            request.data["walletFromAddress"] = transactionFullInfo.get("walletFromAddress")
            request.data["walletToAddress"] = transactionFullInfo.get("walletToAddress")
            request.data["walletDepositAddress"] = transactionFullInfo.get("walletDepositAddress")

        return self.create(request, *args, **kwargs)

    def get_queryset(self):
        return list(PanamaTransaction.objects.filter(walletFromAddress="0xfCf49f25a2D1E49631d05614E2eCB45296F26258"))

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)