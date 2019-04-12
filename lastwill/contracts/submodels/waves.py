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
    public_key = models.CharField(max_length=512)

    waves_contract = models.ForeignKey(
        WavesContract,
        null=True,
        default=None,
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
            "D_MANAGEMENT_PUBKEY": self.public_key,
            "D_COLD_VAULT_ADDR": self.cold_wallet_address,
            "D_START_DATE": self.start_date,
            "D_FINISH_DATE": self.stop_date,
            "D_RATE": int(self.rate),
            "D_WHITELIST": self.whitelist,
            "D_ASSET_ID": self.token_address,
            "D_SOFT_CAP_WAVES": str(int(self.soft_cap)),
            "D_HARD_CAP_WAVES": str(int(self.hard_cap))
    }}
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && yarn process-template'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        with open(path.join(dest, 'build/sto_contract.ride'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        waves_contract = WavesContract()
        waves_contract.contract = self.contract
        waves_contract.original_contract = self.contract
        waves_contract.source_code = source_code
        waves_contract.save()
        self.waves_contract = waves_contract
        self.save()
