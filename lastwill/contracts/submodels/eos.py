import re

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *
from lastwill.settings import EOS_URL, CONTRACTS_DIR, EOS_PASSWORD
from lastwill.settings import EOS_ACCOUNT_NAME, EOS_WALLET_NAME
from exchange_API import to_wish, convert


def unlock_eos_account(wallet_name, password):
    lock_command = 'cleos wallet lock -n {wallet}'.format(wallet=wallet_name)
    if os.system(
            "/bin/bash -c '{command}'".format(command=lock_command)

    ):
        raise Exception('lock command error')

    unlock_command = 'echo {password} | cleos wallet unlock -n {wallet}'.format(
        password=password, wallet=wallet_name
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

    @logging
    @blocking
    @postponable
    def deploy(self):
        wallet_name = NETWORKS[self.contract.network.name]['wallet']
        password = NETWORKS[self.contract.network.name]['eos_password']
        unlock_eos_account(wallet_name, password)
        acc_name = NETWORKS[self.contract.network.name]['address']
        command = [
            'cleos', '-u', EOS_URL, 'push', 'action',
            acc_name, 'create',
            '["{acc_name}","{max_sup} {token}"]'.format(
                acc_name=self.admin_address,
                max_sup=self.maximum_supply,
                token=self.token_short_name
            ), '-p',
            acc_name
        ]
        print('command = ', command)

        attempts_count = 10
        for attempt in range(attempts_count):
            print('attempt', attempt, flush=True)
            stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()
            print(stdout, stderr, flush=True)
            result = re.search('executed transaction: ([\da-f]{64})', stderr.decode())
            if result:
                break
        else:
            raise Exception('cannot make tx with %i attempts' % attempts_count)

        tx_hash = result.group(1)
        print('tx_hash:', tx_hash, flush=True)
        eos_contract = EOSContract()
        eos_contract.tx_hash = tx_hash
        eos_contract.address = acc_name
        eos_contract.contract=self.contract
        eos_contract.save()

        self.eos_contract = eos_contract
        self.save()

        self.contract.state='WAITING_FOR_DEPLOYMENT'
        self.contract.save()


    '''
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
    '''

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
        cost = 0.05 *10**18
        return cost

    def get_arguments(self, eth_contract_attr_name):
        return []

    @logging
    @blocking
    @postponable
    def deploy(self):
        wallet_name = NETWORKS[self.contract.network.name]['wallet']
        password = NETWORKS[self.contract.network.name]['eos_password']
        unlock_eos_account(wallet_name, password)
        acc_name = NETWORKS[self.contract.network.name]['address']
        command = [
            'cleos', '-u', EOS_URL, 'system', 'newaccount',
            acc_name, self.account_name, self.owner_public_key,
            self.active_public_key, '--stake-net', str(self.stake_net_value) + ' EOS',
            '--stake-cpu', str(self.stake_cpu_value) + ' EOS',
            '--buy-ram-kbytes', str(self.buy_ram_kbytes)
        ]
        print('command:', command, flush=True)
        

        attempts_count = 10
        for attempt in range(attempts_count):
            print('attempt', attempt, flush=True)
            stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()
            print(stdout, stderr, flush=True)
            result = re.search('executed transaction: ([\da-f]{64})', stderr.decode())
            if result:
                break
        else:
            raise Exception('cannot make tx with %i attempts' % attempts_count)

        tx_hash = result.group(1)
        print('tx_hash:', tx_hash, flush=True)
        eos_contract = EOSContract()
        eos_contract.tx_hash = tx_hash
        eos_contract.address = acc_name
        eos_contract.contract=self.contract
        eos_contract.save()

        self.eos_contract = eos_contract
        self.save()

        self.contract.state='WAITING_FOR_DEPLOYMENT'
        self.contract.save()

