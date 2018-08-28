import re
import binascii
from os import path

from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *
from lastwill.settings import CONTRACTS_DIR, EOS_ATTEMPTS_COUNT
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

    @classmethod
    def min_cost_eos(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost_eos({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(0.99 * 10 ** 18)

    @staticmethod
    def calc_cost_eos(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(150 * 10 ** 4)

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
        acc_name = NETWORKS[self.contract.network.name]['token_address']
        eos_url = 'http://%s:%s' % (str(NETWORKS[self.contract.network.name]['host']), str(NETWORKS[self.contract.network.name]['port']))
        if self.decimals != 0:
            max_supply = str(self.maximum_supply)[:-self.decimals] + '.' + str(self.maximum_supply)[-self.decimals:]
        else:
            max_supply = str(self.maximum_supply)
        command = [
            'cleos', '-u', eos_url, 'push', 'action',
            acc_name, 'create',
            '["{acc_name}","{max_sup} {token}"]'.format(
                acc_name=self.admin_address,
                max_sup=max_supply,
                token=self.token_short_name
            ), '-p',
            acc_name
        ]
        print('command = ', command)

        for attempt in range(EOS_ATTEMPTS_COUNT):
            print('attempt', attempt, flush=True)
            stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()
            print(stdout, stderr, flush=True)
            result = re.search('executed transaction: ([\da-f]{64})', stderr.decode())
            if result:
                break
        else:
            raise Exception('cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)

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


class ContractDetailsEOSAccount(CommonDetails):
    owner_public_key = models.CharField(max_length=128)
    active_public_key = models.CharField(max_length=128)
    account_name = models.CharField(max_length=50)
    stake_net_value = models.CharField(default='0.01', max_length=20)
    stake_cpu_value = models.CharField(default='0.64', max_length=20)
    buy_ram_kbytes = models.IntegerField(default=4)
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

    @classmethod
    def min_cost_eos(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost_eos({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        cost = 0.05 *10**18
        return cost

    @staticmethod
    def calc_cost_eos(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(100 * 10 ** 4)

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
        eos_url = 'http://%s:%s' % (str(NETWORKS[self.contract.network.name]['host']), str(NETWORKS[self.contract.network.name]['port']))
        command = [
            'cleos', '-u', eos_url, 'system', 'newaccount',
            acc_name, self.account_name, self.owner_public_key,
            self.active_public_key, '--stake-net', str(self.stake_net_value) + ' EOS',
            '--stake-cpu', str(self.stake_cpu_value) + ' EOS',
            '--buy-ram-kbytes', str(self.buy_ram_kbytes),
            '--transfer',
        ]
        print('command:', command, flush=True)
        

        for attempt in range(EOS_ATTEMPTS_COUNT):
            print('attempt', attempt, flush=True)
            stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate()
            print(stdout, stderr, flush=True)
            result = re.search('executed transaction: ([\da-f]{64})', stderr.decode())
            if result:
                break
        else:
            raise Exception('cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)

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


class ContractDetailsEOSICO(CommonDetails):
    soft_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    hard_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    token_short_name = models.CharField(max_length=64)
    admin_address = models.CharField(max_length=50)
    issuer = models.CharField(max_length=50)
    is_transferable_at_once = models.BooleanField(default=False)
    start_date = models.IntegerField()
    stop_date = models.IntegerField()
    rate = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    decimals = models.IntegerField()
    temp_directory = models.CharField(max_length=36)
    allow_change_dates = models.BooleanField(default=False)
    whitelist = models.BooleanField(default=False)
    protected_mode = models.BooleanField(default=False)
    min_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )
    max_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )

    eos_contract_token = models.ForeignKey(
        EOSContract,
        null=True,
        default=None,
        related_name='eos_ico_details_token',
        on_delete=models.SET_NULL
    )
    eos_contract_crowdsale = models.ForeignKey(
        EOSContract,
        null=True,
        default=None,
        related_name='eos_ico_details_crowdsale',
        on_delete=models.SET_NULL
    )

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @classmethod
    def min_cost_eos(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost_eos({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        cost = 2 * 10**18
        return cost

    @staticmethod
    def calc_cost_eos(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(250 * 10 ** 4)

    def get_arguments(self, eth_contract_attr_name):
        return []

    def compile(self):
        if self.temp_directory:
            print('already compiled')
            return
        acc_name = NETWORKS[self.contract.network.name]['address']
        dest, preproc_config = create_directory(
            self,
            sour_path='lastwill/eosio-crowdsale/*',
            config_name='config.h'
        )
        command = (
            "/bin/bash -c 'cd {dest} && ./configure.sh "
            "--issuer {address} --symbol {symbol} --decimals {decimals} "
            "--softcap {soft_cap} --hardcap {hard_cap} "
            "--whitelist {whitelist} --contract {acc_name} "
            "--transferable {transferable} --rate {rate} --ratedenom 100 "
            "--mincontrib {min_wei} --maxcontrib {max_wei} --issuer {issuer}'"
            "> {dest}/config.h").format(
                acc_name=acc_name,
                dest=dest,
                address=self.admin_address,
                symbol=self.token_short_name,
                decimals=self.decimals,
                whitelist="true" if self.whitelist else "false",
                transferable="true" if self.is_transferable_at_once else "false",
                rate=self.rate,
                min_wei=self.min_wei if self.min_wei else 0,
                max_wei=self.max_wei if self.max_wei else 0,
                soft_cap=self.soft_cap,
                hard_cap=self.hard_cap,
                issuer=self.issuer
                )
        print('command = ', command, flush=True)
        if os.system(command):
            raise Exception('error generate config')

        if os.system(
                "/bin/bash -c 'cd {dest} && make'".format(
                    dest=dest)
        ):
            raise Exception('compiler error while deploying')

        with open(path.join(dest, 'crowdsale/crowdsale.abi'), 'rb') as f:
            abi = binascii.hexlify(f.read()).decode('utf-8')
        with open(path.join(dest, 'crowdsale/crowdsale.wasm'), 'rb') as f:
            bytecode = binascii.hexlify(f.read()).decode("utf-8")
        with open(path.join(dest, 'crowdsale.cpp'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        print('types', type(bytecode), type(abi))
        eos_contract_crowdsale = EOSContract()
        eos_contract_crowdsale.contract = self.contract
        eos_contract_crowdsale.original_contract = self.contract
        eos_contract_crowdsale.abi = abi
        eos_contract_crowdsale.bytecode = bytecode
        eos_contract_crowdsale.source_code = source_code
        eos_contract_crowdsale.save()
        self.eos_contract_crowdsale = eos_contract_crowdsale
        self.save()
        self.contract.state='ACTIVE'
        self.contract.save()

    def deploy(self):
        self.compile()
        eos_url = 'http://%s:%s' % (
        str(NETWORKS[self.contract.network.name]['host']),
        str(NETWORKS[self.contract.network.name]['port']))
        acc_name = NETWORKS[self.contract.network.name]['address']
        dest = path.join(CONTRACTS_TEMP_DIR, self.temp_directory)
        if self.decimals != 0:
            max_supply = str(self.hard_cap)[:-self.decimals] + '.' + str(self.hard_cap)[-self.decimals:]
        else:
            max_supply = str(self.hard_cap)
        wallet_name = NETWORKS[self.contract.network.name]['wallet']
        password = NETWORKS[self.contract.network.name]['eos_password']
        our_public_key = NETWORKS[self.contract.network.name]['pub']
        unlock_eos_account(wallet_name, password)
        command = [
            'cleos', '-u', eos_url, 'set', 'abi', self.admin_address,
            path.join(dest, 'crowdsale/crowdsale.abi'), '-jd', '-s'
        ]
        print('command:', command, flush=True)
        for attempt in range(EOS_ATTEMPTS_COUNT):
             print('attempt', attempt, flush=True)
             stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE,
                                    stderr=PIPE).communicate()
             # print('stdout', stdout, stderr)
             abi = json.loads(stdout.decode())['actions'][0]['data'][20:]
             # abi = json.loads(stdout.decode())['actions'][0]['data'][10:].encode("utf-8")
             # print('abi', abi)
             if abi:
                 break
        else:
            raise Exception('cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)

        actions = {
            "actions": [
            {"account": "eosio", "name": "newaccount",
             "authorization":
                 [{"actor": acc_name, "permission": "active"}],
             "data": {"creator": acc_name, "name": self.admin_address,
                      "owner":
                          {"threshold": 1,
                           "keys": [{"key": our_public_key, "weight": 1}],
                           "accounts": [], "waits": []},
                      "active":
                          {"threshold": 1, "keys":
                              [{"key": our_public_key, "weight": 1}],
                           "accounts": [], "waits": []}}},
            {"account": "eosio", "name": "delegatebw",
             "authorization":
                 [{"actor": acc_name, "permission": "active"}],
             "data": {"from": acc_name, "receiver": self.admin_address,
                      "stake_net_quantity": "10.0000 EOS",
                      "stake_cpu_quantity": "10.0000 EOS",
                      "transfer": 0}},
            {"account": "eosio", "name": "buyrambytes",
             "authorization":
                 [{"actor": acc_name, "permission": "active"}],
             "data": {"payer": acc_name, "receiver": self.admin_address,
                      "bytes": 32768}},
            {"account": "eosio", "name": "setcode",
             "authorization":
                 [{"actor": self.admin_address, "permission": "active"}],
             "data": {"account": self.admin_address, "vmtype": 0,
                      "vmversion": 0,
                      "code": self.eos_contract_crowdsale.bytecode}},
            {"account": "eosio", "name": "setabi",
             "authorization":
                 [{"actor": self.admin_address, "permission": "active"}],
             "data": {"account": self.admin_address,
                      "abi": abi}},

            {"account": acc_name, "name": "create",
             "authorization":
                 [{"actor": acc_name, "permission": "active"}],
             "data": {"issuer": self.admin_address,
                      "maximum_supply": max_supply + ' ' + self.token_short_name,
                      "lock": True}},
            {"account": self.admin_address, "name": "init",
             "authorization":
                 [{"actor": self.admin_address, "permission": "active"}],
             "data": {"start": self.start_date, "finish": self.stop_date}},
            {"account": "eosio", "name": "updateauth",
             "authorization": [{
                 "actor": self.admin_address,
                 "permission": "owner"
             }],
             "data": {
                 "account": self.admin_address,
                 "permission": "owner",
                 "parent": "",
                 "auth": {
                     "threshold": 1,
                     "keys": [],
                     "accounts": [{
                         "permission": {
                             "actor": self.admin_address,
                             "permission": "owner"
                         },
                         "weight": 1
                     }],
                     "waits": []
                 }
             }
             }, {
                "account": "eosio",
                "name": "updateauth",
                "authorization": [{
                    "actor": self.admin_address,
                    "permission": "active"
                }],
                "data": {
                    "account": self.admin_address,
                    "permission": "active",
                    "parent": "owner",
                    "auth": {
                        "threshold": 1, "keys": [],
                        "accounts": [{
                            "permission": {
                                "actor": self.admin_address,
                                "permission": "active"
                            },
                            "weight": 1
                        }],
                        "waits": []
                    }
                }
            }]
        }
        print(type(actions))
        with open(path.join(dest, 'deploy_params.json'), 'w') as f:
            f.write(json.dumps(actions))
        command = [
            'cleos', '-u', eos_url, 'push', 'transaction', path.join(dest, 'deploy_params.json')
        ]
        print('command:', command, flush=True)
        print('lenght of command', len(str(command)))

        for attempt in range(EOS_ATTEMPTS_COUNT):
            print('attempt', attempt, flush=True)
            stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE,
                                   stderr=PIPE).communicate()
            print(stdout, stderr, flush=True)
            result = re.search('executed transaction: ([\da-f]{64})',
                               stderr.decode())
            if result:
                break
        else:
            raise Exception(
                'push transaction cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)
        print('SUCCESS')
