import datetime
import time
import random
import string

from ethereum import abi
from ethereum.utils import checksum_encode

from django.db import models
from django.core.mail import send_mail, EmailMessage
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *
from lastwill.settings import SWAPS_MAIL, SITE_PROTOCOL, SWAPS_URL
from lastwill.consts import ETH_ADDRESS, NET_DECIMALS, CONTRACT_GAS_LIMIT
from email_messages import *


class InvestAddresses(models.Model):
    contract = models.ForeignKey(Contract)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )

@contract_details('SWAPS contract')
class ContractDetailsSWAPS(CommonDetails):
    base_address = models.CharField(max_length=50)
    base_limit = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    quote_address = models.CharField(max_length=50)
    quote_limit = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    # active_to = models.DateTimeField()
    stop_date = models.DateTimeField()
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

    def predeploy_validate(self):
        now = timezone.now()
        if self.stop_date < now.timestamp():
            raise ValidationError({'result': 1}, code=400)

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

    @classmethod
    def min_cost_usdt(cls):
        network = Network.objects.get(name='ETHEREUM_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost_usdt(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        result = int(10 * NET_DECIMALS['USDT'])
        return result

    def get_arguments(self, eth_contract_attr_name):
        return [
        ]

    def compile(self, eth_contract_attr_name='eth_contract'):
        print('standalone token contract compile')
        if self.temp_directory:
            print('already compiled')
            return
        dest, preproc_config = create_directory(self, sour_path='lastwill/swaps/*')
        # if os.system('cd {dest} && ./compile-token.sh'.format(dest=dest)):
        preproc_params = {"constants": {
            "D_OWNER": checksum_encode(self.owner_address),
            "D_BASE_ADDRESS": checksum_encode(self.base_address),
            "D_BASE_LIMIT": str(int(self.base_limit)),
            "D_QUOTE_ADDRESS": checksum_encode(self.quote_address),
            "D_QUOTE_LIMIT": str(int(self.quote_limit)),
            "D_EXPIRATION_TS": str(int(time.mktime(self.stop_date.timetuple())))
        }}
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && yarn compile'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        with open(path.join(dest, 'build/contracts/Swaps.json'), 'rb') as f:
            token_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(dest, 'build/Swaps.sol'), 'rb') as f:
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
    def deploy(self, eth_contract_attr_name='eth_contract'):
        link = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        self.unique_link = link
        self.save()
        return super().deploy(eth_contract_attr_name)

    def get_gaslimit(self):
        return CONTRACT_GAS_LIMIT['TOKEN']

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        res = super().msg_deployed(message, 'eth_contract')
        self.eth_contract.address = message['address']
        self.eth_contract.save()
        self.contract.state = 'ACTIVE'
        self.contract.save()
        swaps_link='{protocol}://{url}/public/{unique_link}'.format(
            protocol=SITE_PROTOCOL,
            unique_link=self.unique_link, url=SWAPS_URL
        )
        send_mail(
            swaps_deploed_subject,
            swaps_deploed_message.format(
                swaps_link=swaps_link
            ),
            SWAPS_MAIL,
            [self.contract.user.email]
        )
        return res

    def finalized(self, message):
        self.contract.state = 'DONE'
        self.contract.save()

    def cancelled(self, message):
        self.contract.state = 'CANCELLED'
        self.contract.save()
