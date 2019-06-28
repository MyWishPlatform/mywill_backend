import random
import string
import smtplib
from ethereum.utils import checksum_encode

from django.db import models

from lastwill.contracts.submodels.common import *
from lastwill.settings import SITE_PROTOCOL, SWAPS_URL
from lastwill.settings import EMAIL_HOST_USER_SWAPS, EMAIL_HOST_PASSWORD_SWAPS
from lastwill.consts import NET_DECIMALS, CONTRACT_GAS_LIMIT
from email_messages import *


def sendEMail(sub, text, mail):
    server = smtplib.SMTP('smtp.yandex.ru',587)
    server.starttls()
    server.ehlo()
    server.login(EMAIL_HOST_USER_SWAPS, EMAIL_HOST_PASSWORD_SWAPS)
    message = "\r\n".join([
        "From: {address}".format(address=EMAIL_HOST_USER_SWAPS),
        "To: {to}".format(to=mail),
        "Subject: {sub}".format(sub=sub),
        "",
        str(text)
    ])
    server.sendmail(EMAIL_HOST_USER_SWAPS, mail, message)
    server.quit()


def get_swap_from_orderbook(swap_id):
    backend_contract = OrderBookSwaps.objects.filter(id=swap_id).first()
    saved_details = {
        'id': backend_contract.id,
        'name': backend_contract.name,
        'base_address': backend_contract.base_address,
        'base_limit': backend_contract.base_limit,
        'base_coin_id': backend_contract.base_coin_id,
        'quote_address': backend_contract.quote_address,
        'quote_limit': backend_contract.quote_limit,
        'quote_coin_id': backend_contract.quote_coin_id,
        'owner_address': backend_contract.owner_address,
        'stop_date': backend_contract.stop_date,
        'memo_contract': backend_contract.memo_contract,
        'unique_link': backend_contract.unique_link,
        'state': backend_contract.state
    }
    return saved_details


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
        pass

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
        if self.contract.user.email:
            swaps_link = '{protocol}://{url}/public/{unique_link}'.format(
                protocol=SITE_PROTOCOL,
                unique_link=self.unique_link, url=SWAPS_URL
            )
            sendEMail(
                swaps_deploed_subject,
                swaps_deploed_message.format(swaps_link=swaps_link),
                [self.contract.user.email]
            )
        return res

    def finalized(self, message):
        self.contract.state = 'DONE'
        self.contract.save()

    def cancelled(self, message):
        self.contract.state = 'CANCELLED'
        self.contract.save()


@contract_details('SWAPS contract')
class ContractDetailsSWAPS2(CommonDetails):
    base_address = models.CharField(max_length=50)
    base_limit = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    quote_address = models.CharField(max_length=50)
    quote_limit = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    stop_date = models.DateTimeField()
    public = models.BooleanField(default=True)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    whitelist = models.BooleanField(default=False)
    whitelist_address = models.CharField(max_length=50)
    unique_link = models.CharField(max_length=50)
    memo_contract = models.CharField(max_length=70)

    broker_fee = models.BooleanField(default=False)
    broker_fee_address = models.CharField(max_length=50, null=True, default=None)
    broker_fee_base = models.FloatField(null=True, default=None)
    broker_fee_quote = models.FloatField(null=True, default=None)

    eth_contract = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='swaps2_details',
        on_delete=models.SET_NULL
    )
    temp_directory = models.CharField(max_length=36)

    min_base_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )
    min_quote_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        link = ''.join(
            random.choice(string.ascii_lowercase + string.digits) for _ in
            range(6)
        )
        self.unique_link = link
        self.save()
        self.eth_contract = EthContract()
        self.eth_contract.address = message['address']
        self.eth_contract.tx_hash = message['transactionHash']
        self.eth_contract.save()
        self.contract.state = 'ACTIVE'
        self.contract.save()
        if self.contract.user.email:
            swaps_link = '{protocol}://{url}/public/{unique_link}'.format(
                protocol=SITE_PROTOCOL,
                unique_link=self.unique_link, url=SWAPS_URL
            )
            sendEMail(
                swaps_deploed_subject,
                swaps_deploed_message.format(swaps_link=swaps_link),
                [self.contract.user.email]
            )
        return

    def finalized(self, message):
        self.contract.state = 'DONE'
        self.contract.save()

    def cancelled(self, message):
        self.contract.state = 'CANCELLED'
        self.contract.save()

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


class OrderBookSwaps(models.Model):
    base_address = models.CharField(max_length=50, null=True, default=None)
    base_limit = models.CharField(max_length=512, null=True, default=None)
    base_coin_id = models.IntegerField(default=0)
    quote_address = models.CharField(max_length=50, null=True, default=None)
    quote_limit = models.CharField(max_length=512, null=True, default=None)
    quote_coin_id = models.IntegerField(default=0)
    stop_date = models.DateTimeField()
    public = models.BooleanField(default=True)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    name = models.CharField(max_length=512, null=True)
    state = models.CharField(max_length=63, default='CREATED')
    unique_link = models.CharField(max_length=50, null=True, default=None)
    memo_contract = models.CharField(max_length=70, null=True, default=None)
    user = models.ForeignKey(User)

    broker_fee = models.BooleanField(default=False)
    broker_fee_address = models.CharField(max_length=50, null=True, default=None)
    broker_fee_base = models.FloatField(null=True, default=None)
    broker_fee_quote = models.FloatField(null=True, default=None)

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        self.state = 'ACTIVE'
        self.save()
        return

