import datetime
import binascii
import requests
import json
import base58

from ethereum import abi

# from tronapi import Tron
# from solc import compile_source

from django.db import models
from django.core.mail import send_mail, EmailMessage
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *


def convert_address_to_hex(address):
    # short_addresss = address[1:]
    decode_address = base58.b58decode(address)[1:21]
    hex_address = binascii.hexlify(decode_address)
    hex_address = '0x' + hex_address.decode("utf-8")
    return hex_address


class TRONContract(EthContract):
    pass


@contract_details('Token contract')
class ContractDetailsTRONToken(CommonDetails):
    token_name = models.CharField(max_length=512)
    token_short_name = models.CharField(max_length=64)
    admin_address = models.CharField(max_length=50)
    decimals = models.IntegerField()
    token_type = models.CharField(max_length=32, default='ERC20')
    tron_contract_token = models.ForeignKey(
        TRONContract,
        null=True,
        default=None,
        related_name='token_details',
        on_delete=models.SET_NULL
    )
    future_minting = models.BooleanField(default=False)
    temp_directory = models.CharField(max_length=36)

    def predeploy_validate(self):
        now = timezone.now()
        token_holders = self.contract.tokenholder_set.all()
        for th in token_holders:
            if th.freeze_date:
                if th.freeze_date < now.timestamp() + 600:
                    raise ValidationError({'result': 1}, code=400)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='TRON_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        result = int(2.99 * 10 ** 18)
        return result

    def get_arguments(self, eth_contract_attr_name):
        return []

    @logging
    def compile(self, eth_contract_attr_name='eth_contract_token'):
        print('standalone token contract compile')
        if self.temp_directory:
            print('already compiled')
            self.lgr.append('already compiled')
            return
        dest, preproc_config = create_directory(self, sour_path='lastwill/tron-token/*')
        self.lgr.append('dest %s' % dest)
        token_holders = self.contract.tokenholder_set.all()
        for th in token_holders:
            if th.address.startswith('41'):
                th.address = '0x' + th.address[2:]
                th.save()
            else:
                th.address = convert_address_to_hex(th.address)
                th.save()
        preproc_params = {"constants": {"D_ONLY_TOKEN": True}}
        preproc_params['constants'] = add_token_params(
            preproc_params['constants'], self, token_holders,
            False, self.future_minting
        )
        owner = '0x' + self.admin_address[2:] if self.admin_address.startswith('41') else convert_address_to_hex(self.admin_address)
        preproc_params['constants']['D_CONTRACTS_OWNER'] = owner
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && yarn compile-token'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        with open(path.join(dest, 'build/contracts/MainToken.json'), 'rb') as f:
            token_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'build/MainToken.sol'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        tron_contract_token = TRONContract()
        tron_contract_token.abi = token_json['abi']
        tron_contract_token.bytecode = token_json['bytecode'][2:]
        tron_contract_token.compiler_version = token_json['compiler']['version']
        tron_contract_token.contract = self.contract
        tron_contract_token.original_contract = self.contract
        tron_contract_token.source_code = source_code
        tron_contract_token.save()
        self.tron_contract_token = tron_contract_token
        self.save()

    def deploy(self, eth_contract_attr_name='eth_contract_token'):
        self.compile()
        print('deploy tron token')
        abi = json.dumps(self.tron_contract_token.abi)
        deploy_params = {
            # 'abi': '[]', 'bytecode': '00',
            # "abi": "[{\"constant\":false,\"inputs\":[{\"name\":\"key\",\"type\":\"uint256\"},{\"name\":\"value\",\"type\":\"uint256\"}],\"name\":\"set\",\"outputs\":[],\"payable\":false,\"stateMutability\":\"nonpayable\",\"type\":\"function\"},{\"constant\":true,\"inputs\":[{\"name\":\"key\",\"type\":\"uint256\"}],\"name\":\"get\",\"outputs\":[{\"name\":\"value\",\"type\":\"uint256\"}],\"payable\":false,\"stateMutability\":\"view\",\"type\":\"function\"}]",
            # "bytecode": "608060405234801561001057600080fd5b5060de8061001f6000396000f30060806040526004361060485763ffffffff7c01000000000000000000000000000000000000000000000000000000006000350416631ab06ee58114604d5780639507d39a146067575b600080fd5b348015605857600080fd5b506065600435602435608e565b005b348015607257600080fd5b50607c60043560a0565b60408051918252519081900360200190f35b60009182526020829052604090912055565b600090815260208190526040902054905600a165627a7a72305820fdfe832221d60dd582b4526afa20518b98c2e1cb0054653053a844cf265b25040029",
            'abi': str(abi),
            'bytecode': self.tron_contract_token.bytecode,
            'consume_user_resource_percent': 0,
            'fee_limit': 0,
            'call_value': 0,
            'bandwidth_limit': 1000000,
            'owner_address': convert_address_to_hex(NETWORKS[self.contract.network.name]['address']),
            'origin_energy_limit': 10000000
        }
        deploy_params = json.dumps(deploy_params)
        # print('deploy_params', deploy_params)
        tron_url = 'https://%s:%s' % (str(NETWORKS[self.contract.network.name]['host']), str(NETWORKS[self.contract.network.name]['port']))
        result = requests.post(tron_url + '/wallet/deploycontract', data=deploy_params)
        trx_info = json.loads(result.content.decode())
        trx_info = {"transaction": {"txID":"e828e2c39d68df2f0f1d730470ce7d63d99bcb61a4fcb3897db387b6febb317e","contract_address":"414d2d0841f93924d961c85260b7c57ad370a741a9","raw_data":{"contract":[{"parameter":{"value":{"owner_address":"41928c9af0651632157ef27a2cf17ca72c575a4d21","new_contract":{"bytecode":"00","origin_address":"41928c9af0651632157ef27a2cf17ca72c575a4d21","abi":{}}},"type_url":"type.googleapis.com/protocol.CreateSmartContract"},"type":"CreateSmartContract"}],"ref_block_bytes":"524d","ref_block_hash":"4438d73c7ad3b100","expiration":1545402606000,"timestamp":1545402549425}}, "privateKey": "da146374a75310b9666e834ee4ad0866d6f4035967bfc76217c5a495fff9f0d0"}
        trx_info['privateKey'] = NETWORKS[self.contract.network.name]['private_key']
        trx = json.dumps(trx_info)
        print('trx=', trx, flush=True)
        result = requests.post(tron_url + '/wallet/gettransactionsign', data=trx)
        print(result.content)
        # result = requests.post(tron_url + '/wallet/broadcasttransaction', params=result.json)
        # print(result)

