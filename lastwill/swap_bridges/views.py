from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView

from .models import Swap
from .serializers import SwapModelSerializer
from .services import create_swap


# Create your views here.
class SwapListCreateAPIView(ListCreateAPIView):
    queryset = Swap.objects.filter(is_displayed=True)
    serializer_class = SwapModelSerializer

    def create(self, request):
        network = int(request.data['source_network'])
        tx_hash = request.data['tx_hash']
        response = create_swap(network, tx_hash)

        return Response(*response)
