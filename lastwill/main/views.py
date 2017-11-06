import traceback
import sys
import requests
import json
from django.shortcuts import render_to_response
from django.middleware import csrf
from rest_framework.decorators import api_view
from rest_framework.response import Response
from lastwill.parint import *

def index(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('index.html', {'csrf_token': csrf_token, 'request': request})

@api_view()
def balance(request):
    address = request.query_params.get('address', None)
    try:
        return Response({
                'result': ParInt().eth_getBalance(address),
                'status': 0
        })
    except (ParConnectExc, ParErrorExc) as e:
        return Response({
                'detail': str(e),
                'status': 1
        })
        
        
def login(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('login.html', {'csrf_token': csrf_token, 'request': request})


@api_view()
def eth2rub(request):
    return Response(json.loads(requests.get('https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=RUB').content.decode()))
