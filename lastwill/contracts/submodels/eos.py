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


class EOSContract(models.Model):
    contract = models.ForeignKey(Contract, null=True, default=None)
    original_contract = models.ForeignKey(
        Contract, null=True, default=None, related_name='orig_eoscontract'
    )
    address = models.CharField(max_length=50, null=True, default=None)
    tx_hash = models.CharField(max_length=70, null=True, default=None)

    source_code = models.TextField()
    bytecode = models.TextField()
    abi = JSONField(default={})
    compiler_version = models.CharField(
        max_length=200, null=True, default=None
    )
    constructor_arguments = models.TextField()


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
        c3 = ("""cleos -u {url} push action {our_account} create '\\''["{account_name}", "{max_supply} {token_name}"]'\\'' -p {our_account} {account_name}""")
        command = "/bin/bash -c '" + c3.format(
                    our_account=EOS_ACCOUNT_NAME,
                    url=EOS_URL,
                    account_name=self.admin_address,
                    max_supply=self.maximum_supply,
                    token_name=self.token_short_name
                    )+ "'"
        print('command = ', command)
        if os.system(
                "/bin/bash -c '" + c3.format(
                    url=EOS_URL,
                    account_name=self.admin_address,
                    max_supply=self.maximum_supply,
                    token_name=self.token_short_name
                    )
                + "'"

        ):
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
