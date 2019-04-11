import datetime

from ethereum import abi

from django.db import models
from django.core.mail import send_mail, EmailMessage
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS


class WavesContract(EthContract):
    pass


@contract_details('Waves STO')
class ContractDetailsSTO(CommonDetails):

    soft_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    hard_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    token_address = models.CharField(max_length=512)
    admin_address = models.CharField(max_length=50)
    start_date = models.IntegerField()
    stop_date = models.IntegerField()
    rate = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    temp_directory = models.CharField(max_length=36)
    time_bonuses = JSONField(null=True, default=None)
    amount_bonuses = JSONField(null=True, default=None)
    continue_minting = models.BooleanField(default=False)
    cold_wallet_address = models.CharField(max_length=50, default='')
    allow_change_dates = models.BooleanField(default=False)
    whitelist = models.BooleanField(default=False)

    waves_contract = models.ForeignKey(
        WavesContract,
        null=True,
        default=None,
        related_name='waves contract',
        on_delete=models.SET_NULL
    )

    min_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )
    max_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='WAVES_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        result = int(0.5)
        return result

    @classmethod
    def min_cost_usdt(cls):
        network = Network.objects.get(name='WAVES_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost_usdt(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        result = int(10 * NET_DECIMALS['USDT'])
        return result

    def get_arguments(self, eth_contract_attr_name):
        return []

    def compile(self, eth_contract_attr_name='eth_contract'):
        print('standalone token contract compile')
        if self.temp_directory:
            print('already compiled')
            return
        dest, preproc_config = create_directory(self, sour_path='lastwill/waves-sto-contract/*')
        preproc_params = {"constants": {
            # "D_MANAGEMENT_ADDRESS_PK": self.admin_address,
            "D_COLD_VAULT_PK": self.cold_wallet_address,
            "D_START_HEIGHT": self.start_date,
            "D_FINISH_HEIGHT": self.stop_date,
            "D_RATE": self.rate,
            "D_WHITELIST": self.whitelist,
            "D_ASSET_ID": self.token_address,
            "D_SOFT_CAP_WAVES": int(self.soft_cap),
            "D_HARD_CAP_WAVES": int(self.hard_cap)
    }}
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && yarn process-template'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        # with open(path.join(dest, 'build/contracts/Swaps.json'), 'rb') as f:
        #     token_json = json.loads(f.read().decode('utf-8-sig'))
        # with open(path.join(dest, 'build/Swaps.sol'), 'rb') as f:
        #     source_code = f.read().decode('utf-8-sig')
        # eth_contract = EthContract()
        # eth_contract.abi = token_json['abi']
        # eth_contract.bytecode = token_json['bytecode'][2:]
        # eth_contract.compiler_version = token_json['compiler']['version']
        # eth_contract.contract = self.contract
        # eth_contract.original_contract = self.contract
        # eth_contract.source_code = source_code
        # eth_contract.save()
        # self.eth_contract = eth_contract
        # self.save()
