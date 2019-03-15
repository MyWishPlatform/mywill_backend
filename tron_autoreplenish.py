import json
import time
import math
import requests
import django
django.setup()

from rest_framework.exceptions import ValidationError
from lastwill.contracts.submodels.tron import convert_address_to_hex
from lastwill.consts import TRON_REPLENISH_THRESHOLD


def check_account(network):
    tron_url = 'http://%s:%s' % (str(NETWORKS[network]['host']), str(NETWORKS[network]['port']))
    address = '41' + convert_address_to_hex(NETWORKS[network]['address'])[2:]
    data = {"address": address}
    result = requests.post(tron_url + '/wallet/getaccountresource', data=json.dumps(data))
    account_info = json.loads(result.content.decode())
    net_available = account_info['NetLimit'] - account_info['NetUsed']
    energy_available = account_info['EnergyLimit'] - account_info['EnergyUsed']

    return {
        'net_delta': net_available,
        'energy_delta': energy_available
    }


def freeze_tron_resource(network, amount, resource_name):
    tron_url = 'http://%s:%s' % (str(NETWORKS[network]['host']), str(NETWORKS[network]['port']))
    data = {
        "owner_address": '41' + convert_address_to_hex(NETWORKS[network]['address'])[2:],
        "frozen_balance": amount * TRON_REPLENISH_THRESHOLD['MIN_TRX'],
        "frozen_duration": 3,
        "resource": resource_name
    }
    result = requests.post(tron_url + '/wallet/freezebalance', data=json.dumps(data))
    freeze_tx = json.loads(result.content.decode())
    print('transaction created')
    print(freeze_tx)
    freeze_tx = {'transaction': freeze_tx,
                 'privateKey':  NETWORKS[network]['private_key']}
    trx1 = json.dumps(freeze_tx)
    print('transaction sign')
    sign_res = requests.post(tron_url + '/wallet/gettransactionsign', data=trx1)
    trx_signed = json.loads(sign_res.content.decode())
    trx2 = json.dumps(trx_signed)
    print(trx2)
    for i in range(5):
        print('attempt=', i)
        result = requests.post(tron_url + '/wallet/broadcasttransaction', data=trx2)
        print(result.content.decode())
        answer = json.loads(result.content.decode())
        print('answer=', answer, flush=True)
        if answer['result']:
            params = {'value': trx_signed['txID']}
            result = requests.post(tron_url + '/wallet/gettransactionbyid', data=json.dumps(params))
            ret = json.loads(result.content.decode())
            if ret:
                print('tx_hash=', trx_signed['txID'], flush=True)
                return
        time.sleep(5)
    else:
                raise ValidationError({'result': 1}, code=400)


def check_and_freeze(network):
    account_resources = check_account(network)
    try:
        if account_resources['net_delta'] <= TRON_REPLENISH_THRESHOLD['NET']:
            print('{network_name} Started automatic replenish of NET'.format(network_name=network))
            freeze_tron_resource(network, 1, "BANDWIDTH")
            print('{network_name} Finished automatic replenish'.format(network_name=network))
        else:
            print('{network_name} account NET is above required limit on'.format(network_name=network),
                  account_resources['net_delta'] - TRON_REPLENISH_THRESHOLD['NET']
                  )
        if account_resources['energy_delta'] <= TRON_REPLENISH_THRESHOLD['ENERGY']:
            print('{network_name} Started automatic replenish of ENERGY'.format(network_name=network))
            trx_energy_amount = math.ceil(TRON_REPLENISH_THRESHOLD['ENERGY'] / TRON_REPLENISH_THRESHOLD['MIN_TRX'])
            freeze_tron_resource(network, trx_energy_amount, "ENERGY")
            print('{network_name} Finished automatic replenish'.format(network_name=network))
        else:
            print('{network_name} account resource is above required limit on'.format(network_name=network),
                  account_resources['energy_delta'] - TRON_REPLENISH_THRESHOLD['ENERGY']
                  )
    except Exception as e:
        print(e)
        print('TRON autoreplenish failed')
