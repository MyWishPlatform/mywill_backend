import re

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *
from lastwill.settings import EOS_URL, CONTRACTS_DIR, EOS_PASSWORD
from lastwill.settings import EOS_ACCOUNT_NAME, EOS_WALLET_NAME


def unlock_eos_account():
    lock_command = 'cleos wallet lock -n {wallet}'.format(wallet=EOS_WALLET_NAME)
    if os.system(
            "/bin/bash -c '{command}'".format(command=lock_command)

    ):
        raise Exception('lock command error')

    unlock_command = 'echo {password} | cleos wallet unlock -n {wallet}'.format(
        password=EOS_PASSWORD, wallet=EOS_WALLET_NAME
    )
    if os.system(
            "/bin/bash -c '{command}'".format(command=unlock_command)

    ):
        raise Exception('unlock command error')


class EOSContract(EthContract):
    pass


class ContractDetailsEOSToken(CommonDetails):
    token_short_name = models.CharField(max_length=64)
    admin_address = models.CharField(max_length=50)
    decimals = models.IntegerField()
    eos_contract = models.ForeignKey(
        EOSContract,
        null=True,
        default=None,
        related_name='eos_token_details',
        on_delete=models.SET_NULL
    )
    temp_directory = models.CharField(max_length=36)
    maximum_supply = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    easy_token = models.BooleanField(default=True)

    def predeploy_validate(self):
        now = timezone.now()
        token_holders = self.contract.eostokenholder_set.all()
        for th in token_holders:
            if th.freeze_date:
                if th.freeze_date < now.timestamp() + 600:
                    raise ValidationError({'result': 1}, code=400)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(0.99 * 10 ** 18)

    def get_arguments(self, eth_contract_attr_name):
        return []

    def get_stake_params(self):
        return {
            'stake_net': '10.0000 EOS',
            'stake_cpu': '10.0000 EOS',
            'buy_ram_kbytes': 128
        }

    # @logging
    # @blocking
    # @postponable
    def deploy(self):
        # self.compile()
        # params = {"account_name": 'mywishio'}
        # req = requests.post(EOS_URL + 'v1/chain/get_account', json=params)
        # key = ''
        # for x in req['permissions']:
        #     if x['perm_name'] == 'active' and x['parent'] == 'owner':
        #         key = x['required_auth']['keys'][0]['key']
        #
        # c1 = ('cleos -u {url} system newaccount mywishio {account_name} '
        #      '{key1} {key2} --stake-net {s_net} --stake-cpu {s_cpu} '
        #      '--buy-ram-kbytes {ram}')
        # params = self.get_stake_params()
        # if os.system(
        #         "/bin/bash -c '" + c1 + "'".format(
        #             url=EOS_URL,
        #             account_name=self.admin_address,
        #             key1=key, key2=key,
        #             s_net=params['stake-net'],
        #             s_cpu=params['stake_cpu'],
        #             ram=params['buy_ram_kbytes']
        #             )
        #
        # ):
        #     raise Exception('deploy error 1')

        # c2 = 'cleos -u {url} set contract {account_name} {contract_path}'
        # if os.system(
        #         "/bin/bash -c '" + c2 + "'".format(
        #             url=EOS_URL,
        #             account_name=self.admin_address,
        #             contract_path=CONTRACTS_DIR + 'eosio.token/eosio.token/'
        #             )
        #
        # ):
        #     raise Exception('deploy error 2')
        unlock_eos_account()
        command = [
            'cleos', '-u', EOS_URL, 'push', 'action',
            EOS_ACCOUNT_NAME, 'create',
            '["{acc_name}","{max_sup} {token}"]'.format(
                acc_name=self.admin_address,
                max_sup=self.maximum_supply,
                token=self.token_short_name
            ), '-p',
            EOS_ACCOUNT_NAME, self.admin_address
        ]
        print('command = ', command)
        result = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()
        print('result  ', result)
        try:
            tx_hash = re.match('executed transaction: ([\da-f]{64})',
                               result[1].decode()).group(1)
            print('tx_hash ', tx_hash)
            eos_contract = EOSContract()
            eos_contract.tx_hash = tx_hash
            eos_contract.address = EOS_ACCOUNT_NAME
            eos_contract.contract=self.contract
            eos_contract.save()
        except:
            raise Exception('deploy error')
        self.contract.state='WAITING_FOR_DEPLOYMENT'
        self.contract.save()

    def compile(self):
        dest = path.join(CONTRACTS_DIR, 'eosio.token/')
        with open(path.join(dest, 'eosio.token/eosio.token/eosio.token.abi'), 'rb') as f:
            abi = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'eosio.token/eosio.token/eosio.token.wasm'), 'rb') as f:
            bytecode = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'eosio.token/eosio.token.cpp'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        eos_contract = EOSContract()
        eos_contract.abi = abi
        eos_contract.bytecode = bytecode
        eos_contract.contract = self.contract
        eos_contract.original_contract = self.contract
        eos_contract.source_code = source_code
        eos_contract.save()
        self.save()

    def created(self, message):
        self.contract.state='ACTIVE'
        self.contract.save()


class ContractDetailsEOSAccount(CommonDetails):
    owner_public_key = models.CharField(max_length=128)
    active_public_key = models.CharField(max_length=128)
    account_name = models.CharField(max_length=50)
    stake_net_value = models.CharField(default='10.0000', max_length=20)
    stake_cpu_value = models.CharField(default='10.0000', max_length=20)
    buy_ram_kbytes = models.IntegerField(default=128)
    eos_contract = models.ForeignKey(
        EOSContract,
        null=True,
        default=None,
        related_name='eos_account_details',
        on_delete=models.SET_NULL
    )

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return 5000

    def get_arguments(self, eth_contract_attr_name):
        return []

    # @logging
    # @blocking
    # @postponable
    def deploy(self):
        unlock_eos_account()
        command = [
            'cleos', '-u', EOS_URL, 'system', 'newaccount',
            EOS_ACCOUNT_NAME, self.account_name, self.owner_public_key,
            self.active_public_key, '--stake-net', '"%s"' % (str(self.stake_net_value) + ' EOS'),
            ' --stake-cpu ', '"%s"' % (str(self.stake_cpu_value) + ' EOS'),
            '--buy-ram-kbytes ' + str(self.buy_ram_kbytes)
        ]
        print('command = ', command)
        result = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()
        print('result  ', result)
        try:
            tx_hash = re.match('executed transaction: ([\da-f]{64})',
                               result[1].decode()).group(1)
            print('tx_hash ', tx_hash)
            eos_contract = EOSContract()
            eos_contract.tx_hash = tx_hash
            eos_contract.address = EOS_ACCOUNT_NAME
            eos_contract.contract=self.contract
            eos_contract.save()
        except:
            raise Exception('create account error')
        self.contract.state='WAITING_FOR_DEPLOYMENT'
        self.contract.save()

    def msg_deployed(self, message):
        self.contract.state='ACTIVE'
        self.contract.save()
