import datetime

from ethereum import abi

from django.db import models
from django.core.mail import send_mail, EmailMessage
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *
from lastwill.settings import SUPPORT_EMAIL, CONTRACTS_TEMP_DIR
from lastwill.consts import CONTRACT_PRICE_ETH, NET_DECIMALS, CONTRACT_GAS_LIMIT
from email_messages import *


class InvestAddresses(models.Model):
    contract = models.ForeignKey(Contract)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )

@contract_details('SWAPS contract')
class ContractDetailsSWAPS(CommonDetails):
    owner_token_address = models.CharField(max_length=50)
    owner_token_value = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    investor_token_address = models.CharField(max_length=50)
    investor_token_value = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    active_to = models.DateTimeField()
    public = models.BooleanField(default=True)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    unique_link = models.CharField(max_length=50)

    eth_contract = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='swaps_details',
        on_delete=models.SET_NULL
    )
    temp_directory = models.CharField(max_length=36)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='ETHEREUM_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        result = int(0.5 * NET_DECIMALS['ETH'])
        return result

    def get_arguments(self, eth_contract_attr_name):
        return [
            self.owner_address,
            self.owner_token_address,
            self.owner_token_value,
            self.investor_token_address,
            self.investor_token_value,
            self.active_to
        ]

    def compile(self, eth_contract_attr_name='eth_contract'):
        print('standalone token contract compile')
        if self.temp_directory:
            print('already compiled')
            return
        dest, preproc_config = create_directory(self, sour_path='lastwill/swaps/*')
        # if os.system('cd {dest} && ./compile-token.sh'.format(dest=dest)):
        if os.system('cd {dest} && yarn compile'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        with open(path.join(dest, 'build/contracts/Swaps.json'), 'rb') as f:
            token_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'contracts/Swaps.sol'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        eth_contract = EthContract()
        eth_contract.abi = token_json['abi']
        eth_contract.bytecode = token_json['bytecode'][2:]
        eth_contract.compiler_version = token_json['compiler']['version']
        eth_contract.contract = self.contract
        eth_contract.original_contract = self.contract
        eth_contract.source_code = source_code
        eth_contract.save()
        self.eth_contract = eth_contract
        self.save()

    @blocking
    @postponable
    def deploy(self, eth_contract_attr_name='eth_contract_token'):
        return super().deploy(eth_contract_attr_name)

    def get_gaslimit(self):
        return CONTRACT_GAS_LIMIT['TOKEN']

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        res = super().msg_deployed(message, 'eth_contract')
        self.contract.state = 'ACTIVE'
        self.contract.save()
        return res
