import traceback
import sys
import binascii
from ethereum import abi
import requests
import json
from django.shortcuts import render_to_response
from django.middleware import csrf
from django.views.generic import View
from rest_framework.decorators import api_view
from rest_framework.response import Response
from lastwill.parint import *
from exchange_API import convert
from lastwill.settings import SIGNER, DEPLOY_ADDR


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
    return Response(convert('ETH', 'RUB'))

@api_view()
def exc_rate(request):
    return Response(convert(request.query_params.get('fsym'), request.query_params.get('tsyms')))

