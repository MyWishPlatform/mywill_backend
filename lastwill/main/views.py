import traceback
import sys
import requests
import json
from django.shortcuts import render_to_response
from django.middleware import csrf
from rest_framework.decorators import api_view
from rest_framework.response import Response

def index(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('index.html', {'csrf_token': csrf_token, 'request': request})

@api_view()
def balance(request):
    address = request.query_params.get('address', None)
    try:
        response = requests.post('http://127.0.0.1:8545', json={
                'method': 'eth_getBalance',
                'params': [address],
                'id': 1,
                'jsonrpc': '2.0'
        }, headers = {'content-type': 'application/json'})
#        return Response(response)
        balance = json.loads(response.content.decode())['result']
        return Response({'status': '0', 'result': int(balance, 16)})
    except:
        return Response({'status': 1, 'detail': '\n'.join(traceback.format_exception(*sys.exc_info()))})

def login(request):
    csrf_token = csrf.get_token(request)
    return render_to_response('login.html', {'csrf_token': csrf_token, 'request': request})
