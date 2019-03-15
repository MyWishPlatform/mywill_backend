import json
import time
import math
import requests
import django
django.setup()

from rest_framework.exceptions import ValidationError
from lastwill.contracts.submodels.tron import convert_address_to_hex
from lastwill.consts import TRON_REPLENISH_THRESHOLD
from lastwill.settings import TRON_REPLENISH_ACCOUNT, TRON_REPLENISH_CHECK_ACCOUNT


def check_account(account_params, tron_url):
    data = {"address": account_params['address']}
    result = requests.post(tron_url + '/wallet/getaccountresource', data=json.dumps(data))
    account_info = json.loads(result.content.decode())
    net_available = account_info['NetLimit'] - account_info['NetUsed']
    energy_available = account_info['EnergyLimit'] - account_info['EnergyUsed']

    return {
        'net_delta': net_available,
        'energy_delta': energy_available
    }


def freeze_tron_resource(account_params, tron_url, amount, resource_name):
    data = {
        "owner_address": account_params['address'],
        "frozen_balance": amount * TRON_REPLENISH_THRESHOLD['MIN_TRX'],
        "frozen_duration": 3,
        "resource": resource_name
    }
    result = requests.post(tron_url + '/wallet/freezebalance', data=json.dumps(data))
    freeze_tx = json.loads(result.content.decode())
    print('transaction created')
    print(freeze_tx)
    freeze_tx = {'transaction': freeze_tx,
                 'privateKey':  account_params['private_key']}
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


def check_and_freeze(account_params, tron_url):
    account_resources = check_account(tron_url)
    try:
        if account_resources['net_delta'] <= TRON_REPLENISH_THRESHOLD['NET']:
            print('Started automatic replenish of NET for {addr}'.format(addr=account_params["address"]))
            freeze_tron_resource(account_params, tron_url, 1, "BANDWIDTH")
            print('Finished automatic replenish'.format(network_name=network))
        else:
            print('account {addr} NET is above required limit on'.format(addr=account_params["address"]),
                  account_resources['net_delta'] - TRON_REPLENISH_THRESHOLD['NET']
                  )
        if account_resources['energy_delta'] <= TRON_REPLENISH_THRESHOLD['ENERGY']:
            print('Started automatic replenish of ENERGY for {addr}'.format(addr=account_params["address"]))
            trx_energy_amount = math.ceil(TRON_REPLENISH_THRESHOLD['ENERGY'] / TRON_REPLENISH_THRESHOLD['MIN_TRX'])
            freeze_tron_resource(account_params, tron_url, trx_energy_amount, "ENERGY")
            print('Finished automatic replenish'.format(network_name=network))
        else:
            print('account {addr} ENERGY is above required limit on'.format(addr=account_params["address"]),
                  account_resources['energy_delta'] - TRON_REPLENISH_THRESHOLD['ENERGY']
                  )
    except Exception as e:
        print(e)
        print('TRON autoreplenish for {addr} failed'.format(addr=account_params["address"]))


def convert_trx_resources(network):
    tron_url = 'http://%s:%s' % (str(NETWORKS[network]['host']), str(NETWORKS[network]['port']))
    # account_parameters = {
    #     "address": '41' + convert_address_to_hex(NETWORKS[network]['address'])[2:],
    #     "private_key": NETWORKS[network]['private_key']
    # }
    account_main = {
        "address": '41' + convert_address_to_hex(TRON_REPLENISH_ACCOUNT['address']),
        "private_key": TRON_REPLENISH_ACCOUNT['private_key']
    }
    account_check = {
        "address": '41' + convert_address_to_hex(TRON_REPLENISH_CHECK_ACCOUNT['address']),
        "private_key": TRON_REPLENISH_CHECK_ACCOUNT['private_key']
    }

    check_and_freeze(account_main, tron_url)
    check_and_freeze(account_check, tron_url)
