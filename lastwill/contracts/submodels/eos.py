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
        return int(2.99 * 10 ** 18)

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
            print('stderr', stderr, flush=True)
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

    def tokenCreated(self, message):
        self.msg_deployed(message, eth_contract_attr_name='eos_contract')


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

    @staticmethod
    def calc_cost_eos(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        eos_url = 'http://%s:%s' % (
            str(NETWORKS[network.name]['host']),
            str(NETWORKS[network.name]['port'])
        )

        command1 = [
            'cleos', '-u', eos_url, 'get', 'table', 'eosio', 'eosio', 'rammarket'
        ]
        for attempt in range(EOS_ATTEMPTS_COUNT):
            print('attempt', attempt, flush=True)
            stdout, stderr = Popen(command1, stdin=PIPE, stdout=PIPE,
                                   stderr=PIPE).communicate()
            print(stdout, stderr, flush=True)
            result = stdout.decode()
            if result:
                ram = json.loads(result)['rows'][0]
                print('result', result, flush=True)
                print('ram', ram, flush=True)
                print('quote', ram['quote']['balance'].split(), flush=True)
                print('base', ram['base']['balance'].split(), flush=True)
                ram_price = float(ram['quote']['balance'].split()[0]) / float(ram['base']['balance'].split()[0]) * 1024
                break
        else:
            print('stderr', stderr, flush=True)
            raise Exception(
                'cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)
        print('get ram price', flush=True)
        eos_cost = (
                kwargs['buy_ram_kbytes'] * ram_price
                + float(kwargs['stake_net_value'])
                 + float(kwargs['stake_cpu_value'])
        ) * 2
        print('eos cost', eos_cost, flush=True)
        return round(eos_cost, 0) * 10 ** 4

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        # cost = 0.05 *10**18
        eos_cost = ContractDetailsEOSAccount.calc_cost_eos(kwargs, network) / 10 ** 4
        cost = eos_cost * convert('EOS', 'ETH')['ETH']
        print('convert eos cost', cost, flush=True)
        return round(cost, 2) * 10**18

    def get_arguments(self, eth_contract_attr_name):
        return []

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost(
            {
            'stake_cpu_value': '0.64',
            'stake_net_value': '0.01',
            'buy_ram_kbytes': 4
        }, network
        )
        return cost

    @classmethod
    def min_cost_eos(cls):
        network = Network.objects.get(name='EOS_MAINNET')
        cost = cls.calc_cost_eos({
            'stake_cpu_value': '0.64',
            'stake_net_value': '0.01',
            'buy_ram_kbytes': 4
        }, network)
        return cost

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
            print('stderr', stderr, flush=True)
            raise Exception('cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)

        tx_hash = result.group(1)
        print('tx_hash:', tx_hash, flush=True)
        eos_contract = EOSContract()
        eos_contract.tx_hash = tx_hash
        eos_contract.address = self.account_name
        eos_contract.contract=self.contract
        eos_contract.save()

        self.eos_contract = eos_contract
        self.save()

        self.contract.state = 'WAITING_FOR_DEPLOYMENT'
        self.contract.save()

    def newAccount(self, message):
        self.msg_deployed(message, eth_contract_attr_name='eos_contract')


class ContractDetailsEOSICO(CommonDetails):
    soft_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    hard_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    token_short_name = models.CharField(max_length=64)
    crowdsale_address = models.CharField(max_length=50)
    admin_address = models.CharField(max_length=50)
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
        cost = 5 * 10**18
        return cost

    @staticmethod
    def calc_cost_eos(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(250 * 10 ** 4)

    def get_arguments(self, eth_contract_attr_name):
        return []

    def predeploy_validate(self):
        now = timezone.now()
        if self.start_date < now.timestamp() + 600:
            raise ValidationError({'result': 1}, code=400)

    def compile(self):
        if self.temp_directory:
            print('already compiled')
            return
        token_holders = self.contract.eostokenholder_set.all()
        mint = ''
        for th in token_holders:
            mint = mint + ' --mint ' + '"{address} {amount}"'.format(
                address=th.address, amount=th.amount
            )
        print('mint', mint, flush=True)
        token_address = NETWORKS[self.contract.network.name]['token_address']
        dest, preproc_config = create_directory(
            self,
            sour_path='lastwill/eosio-crowdsale/*',
            config_name='config.h'
        )
        command = (
            "/bin/bash -c 'cd {dest} && ./configure.sh "
            "--issuer {issuer} --symbol {symbol} --decimals {decimals} "
            "--softcap {soft_cap} --hardcap {hard_cap} "
            "--whitelist {whitelist} --contract {acc_name} "
            "--transferable {transferable} --rate {rate} --ratedenom 1 "
            "--mincontrib {min_wei} --maxcontrib {max_wei} "
            " {mint} > {dest}/config.h' ").format(
                acc_name=token_address,
                dest=dest,
                # address=self.crowdsale_address,
                symbol=self.token_short_name,
                decimals=self.decimals,
                whitelist="true" if self.whitelist else "false",
                transferable="true" if self.is_transferable_at_once else "false",
                rate=self.rate,
                min_wei=self.min_wei if self.min_wei else 0,
                max_wei=self.max_wei if self.max_wei else 0,
                soft_cap=self.soft_cap,
                hard_cap=self.hard_cap,
                issuer=self.admin_address,
                mint=mint
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
        eos_contract_crowdsale.address = self.crowdsale_address
        eos_contract_crowdsale.abi = abi
        eos_contract_crowdsale.bytecode = bytecode
        eos_contract_crowdsale.source_code = source_code
        eos_contract_crowdsale.save()
        self.eos_contract_crowdsale = eos_contract_crowdsale
        self.save()

    @logging
    @blocking
    @postponable
    def deploy(self):
        self.compile()
        wallet_name = NETWORKS[self.contract.network.name]['wallet']
        password = NETWORKS[self.contract.network.name]['eos_password']
        unlock_eos_account(wallet_name, password)
        acc_name = NETWORKS[self.contract.network.name]['address']
        our_public_key = NETWORKS[self.contract.network.name]['pub']
        eos_url = 'http://%s:%s' % (
        str(NETWORKS[self.contract.network.name]['host']),
        str(NETWORKS[self.contract.network.name]['port']))
        net = NETWORKS[self.contract.network.name]['stake_net']
        cpu = NETWORKS[self.contract.network.name]['stake_cpu']
        ram = NETWORKS[self.contract.network.name]['ram']
        command = [
            'cleos', '-u', eos_url, 'system', 'newaccount',
            acc_name, self.crowdsale_address, our_public_key, our_public_key,
            '--stake-net', net,
            '--stake-cpu', cpu,
            '--buy-ram-kbytes', ram, '--transfer',
        ]
        print('command:', command, flush=True)

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
            print('stderr', stderr, flush=True)
            raise Exception(
                'create account cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)

        tx_hash = result.group(1)
        print('tx_hash:', tx_hash, flush=True)
        print('account for eos ico created', flush=True)
        self.eos_contract_crowdsale.tx_hash = tx_hash
        self.eos_contract_crowdsale.save()

    @logging
    @blocking
    @postponable
    def newAccount(self, message):
        eos_url = 'http://%s:%s' % (
        str(NETWORKS[self.contract.network.name]['host']),
        str(NETWORKS[self.contract.network.name]['port']))
        acc_name = NETWORKS[self.contract.network.name]['address']
        our_public_key = NETWORKS[self.contract.network.name]['pub']
        token_address = NETWORKS[self.contract.network.name]['token_address']
        dest = path.join(CONTRACTS_TEMP_DIR, self.temp_directory)
        token_holders = self.contract.eostokenholder_set.all()
        total_supply = self.hard_cap
        for th in token_holders:
            total_supply = total_supply + th.amount
        if self.decimals != 0:
            if len(str(total_supply)) == self.decimals:
                max_supply = '0.' + str(total_supply)
            else:
                max_supply = str(total_supply)[:-self.decimals] + '.' + str(total_supply)[-self.decimals:]
        else:
            max_supply = str(total_supply)
        print('total supply', max_supply, flush=True)
        wallet_name = NETWORKS[self.contract.network.name]['wallet']
        password = NETWORKS[self.contract.network.name]['eos_password']
        unlock_eos_account(wallet_name, password)
        command = [
            'cleos', '-u', eos_url, 'set', 'abi', self.crowdsale_address,
            path.join(dest, 'crowdsale/crowdsale.abi'), '-jd', '-s'
        ]
        print('command:', command, flush=True)
        for attempt in range(EOS_ATTEMPTS_COUNT):
             print('attempt', attempt, flush=True)
             stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE,
                                    stderr=PIPE).communicate()
             abi = json.loads(stdout.decode())['actions'][0]['data'][20:]
             if abi:
                 break
        else:
            print('stderr', stderr, flush=True)
            raise Exception('cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)

        unlock_eos_account(wallet_name, password)
        dates = json.dumps({'start': self.start_date, 'finish': self.stop_date})
        print(dates, flush=True)
        command = [
            'cleos', '-u', eos_url, 'convert', 'pack_action_data',
            'mywishtest15', 'init', str(dates)
        ]
        print('command:', command, flush=True)
        for attempt in range(EOS_ATTEMPTS_COUNT):
             print('attempt', attempt, flush=True)
             stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE,
                                    stderr=PIPE).communicate()
             init_data = stdout.decode().replace('\n', '')
             print('init_data', init_data)
             if init_data:
                 break
        else:
            print('stderr', stderr, flush=True)
            raise Exception('cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)

        actions = {
                    "actions": [
                        {
                        "account": "eosio",
                        "name": "updateauth",
                        "authorization": [{
                            "actor": self.crowdsale_address,
                            "permission": "active"
                        }],
                         "data": {
                             "account": self.crowdsale_address,
                             "permission": "active", "parent": "owner",
                             "auth": {"threshold": 1, "keys":
                                      [{
                                        "key": our_public_key,
                                        "weight": 1}],
                                        "accounts": [{"permission": {
                                        "actor": self.crowdsale_address,
                                        "permission": "eosio.code"},
                                                "weight": 1}],
                                    "waits": []}}},

                        {
                        "account": "eosio",
                        "name": "setcode",
                        "authorization": [{
                            "actor": self.crowdsale_address,
                            "permission": "active"
                        }],
                        "data": {
                            "account": self.crowdsale_address,
                            "vmtype": 0,
                            "vmversion": 0,
                            "code": self.eos_contract_crowdsale.bytecode
                        }
                    }, {
                        "account": "eosio",
                        "name": "setabi",
                        "authorization": [{
                            "actor": self.crowdsale_address,
                            "permission": "active"
                        }],
                        "data": {
                            "account": self.crowdsale_address,
                            "abi": abi
                        }
                    }, {
                        "account": token_address,
                        "name": "create",
                        "authorization": [{
                            "actor": token_address,
                            "permission": "active"
                        }],
                        "data": {
                            "issuer": self.crowdsale_address,
                            "maximum_supply": max_supply + " " + self.token_short_name,
                            "lock": not self.is_transferable_at_once
                        }
                    },
                    {
                        "account": self.crowdsale_address,
                        "name": "init",
                        "authorization": [{
                            "actor": self.crowdsale_address,
                            "permission": "active"
                        }],
                        "data": init_data
                    },
                    {
                        "account": "eosio",
                        "name": "updateauth",
                        "authorization": [{
                            "actor": self.crowdsale_address,
                            "permission": "owner"
                        }],
                        "data": {
                            "account": self.crowdsale_address,
                            "permission": "owner",
                            "parent": "",
                            "auth": {
                                "threshold": 1,
                                "keys": [],
                                "accounts": [{
                                    "permission": {
                                        "actor": self.crowdsale_address,
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
                            "actor": self.crowdsale_address,
                            "permission": "active"
                        }],
                        "data": {
                            "account": self.crowdsale_address,
                            "permission": "active",
                            "parent": "owner",
                            "auth": {
                                "threshold": 1,
                                "keys": [],
                                "accounts": [{
                                    "permission": {
                                        "actor": self.crowdsale_address,
                                        "permission": "eosio.code"
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
            'cleos', '-u', eos_url, 'push', 'transaction',
            path.join(dest, 'deploy_params.json'),
            '-p', acc_name, '-p', self.crowdsale_address # do we need -p token_addres if address diff from token_address?
        ]
        print('command:', command, flush=True)
        print('lenght of command', len(str(command)))

        for attempt in range(EOS_ATTEMPTS_COUNT):
            print('attempt', attempt, flush=True)
            stdout, stderr = Popen(command, stdin=PIPE, stdout=PIPE,
                                   stderr=PIPE).communicate()
            # print(stdout, stderr, flush=True)
            print(type(stdout), len(stdout), flush=True)
            result = stdout.decode()
            if result:
                result = json.loads(stdout.decode())['transaction_id']
                print(result)
                break
        else:
            print('stderr', stderr, flush=True)
            raise Exception(
                'push transaction cannot make tx with %i attempts' % EOS_ATTEMPTS_COUNT)
        print('SUCCESS')
        self.contract.state = 'WAITING_FOR_DEPLOYMENT'
        self.contract.save()
        self.eos_contract_crowdsale.tx_hash = result
        self.eos_contract_crowdsale.save()

    def initialized(self, message):
        print("eos crowdsale initialized msg", flush=True)
        eos_contract_token = EOSContract()
        token_address = NETWORKS[self.contract.network.name]['token_address']
        eos_contract_token.address = token_address
        eos_contract_token.contract = self.contract
        eos_contract_token.save()
        self.eos_contract_token = eos_contract_token
        self.save()
        self.contract.state = 'ACTIVE'
        self.contract.save()
        
        take_off_blocking(self.contract.network.name, self.contract.id)

    def setcode(self, message):
        return

    def msg_deployed(self, message):
        pass

    def tokenCreated(self, message):
        pass

    def timesChanged(self, message):
        if 'startTime' in message and message['startTime']:
            self.start_date = message['startTime']
        if 'endTime' in message and message['endTime']:
            self.stop_date = message['endTime']
        self.save()

    @logging
    def finalized(self, message):
        self.contract.state = 'DONE'
        self.contract.save()

class EOSAirdropAddress(models.Model):
    contract = models.ForeignKey(Contract, null=True)
    address = models.CharField(max_length=50, db_index=True)
    active = models.BooleanField(default=True)
    state = models.CharField(max_length=10, default='added')
    amount = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True,
        db_index=True
    )


class ContractDetailsEOSAirdrop(CommonDetails):

    contract = models.ForeignKey(Contract, null=True)
    admin_address = models.CharField(max_length=50)
    token_address = models.CharField(max_length=50)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)
