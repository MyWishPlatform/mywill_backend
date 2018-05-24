#!/usr/bin/env python3
import json
import requests
import sys
from lastwill.settings import NETWORKS

class ParConnectExc(Exception):
    def __init__(self, *args):
        self.value = 'can not connect to parity'

    def __str__(self):
        return self.value

class ParErrorExc(Exception):
    pass

    
class ParInt:
    def __init__(self, network=None):
        if network is None:
            if len(sys.argv) > 1 and sys.argv[1] in NETWORKS:
                network = sys.argv[1]
            else:
                network = 'ETHEREUM_MAINNET'
        print('network', network, type(network))
        self.addr = NETWORKS[network]['host']
        self.port = NETWORKS[network]['port']
        print('parity interface', self.addr, self.port, flush=True)


    def __getattr__(self, method):
        def f(*args):
            arguments = { 
                    'method': method,
                    'params': args,
                    'id': 1,
                    'jsonrpc': '2.0',
            }
            try:
                temp = requests.post(
                        'http://{}:{}/'.format(self.addr, self.port),
                        json=arguments,
                        headers = {'Content-Type': 'application/json'}
                )
            except requests.exceptions.ConnectionError as e:
                raise ParConnectExc()
            result = json.loads(temp.content.decode())
            if result.get('error'):
                if 'message' in result['error']:
                    raise ParErrorExc(result['error']['message'])
                else:
                    raise ParErrorExc(result['error'])
            return result['result']
        return f


class NeoInt(ParInt):
    pass
