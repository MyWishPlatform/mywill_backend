from subprocess import Popen, PIPE
from os import path
import os
import uuid
import requests
import json
import binascii
import sha3
import datetime
import shutil
from ethereum import abi
from django.db import models
from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from lastwill.settings import ORACLIZE_PROXY, SIGNER, SOLC, CONTRACTS_DIR, CONTRACTS_TEMP_DIR
from lastwill.parint import *
import lastwill.check as check


contract_details_types = []

def contract_details(name):
    def w(c):
        contract_details_types.append({
                'name': name,
                'model': c,
        })
        return c
    return w


MAX_WEI_DIGITS = len(str(2**256))

'''
contract as user see it at site. contract as service. can contain more then one real ethereum contracts
'''
class Contract(models.Model):
    name = models.CharField(max_length=200, null=True, default=None)
    user = models.ForeignKey(User)
    address = models.CharField(max_length=50, null=True, default=None)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    user_address = models.CharField(max_length=50, null=True, default=None)
    state = models.CharField(max_length=63, default='CREATED')
    created_date = models.DateTimeField(auto_now=True)
    source_code = models.TextField()
    bytecode = models.TextField()
    abi = JSONField(default={})
    compiler_version = models.CharField(max_length=200, null=True, default=None)
    check_interval = models.IntegerField(null=True, default=None)
    active_to = models.DateTimeField(null=True, default=None)
    balance = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True, default=None)
    cost = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
    contract_type = models.IntegerField(default=0)




    def save(self, *args, **kwargs):
        # disable balance saving to prevent collisions with java daemon
        print(args)
        if self.id:
            kwargs['update_fields'] = list(
                    {f.name for f in Contract._meta.fields if f.name not in ('balance', 'id')}
                    &
                    set(kwargs.get('update_fields', [f.name for f in Contract._meta.fields]))
            )
        return super().save(*args, **kwargs)

    def get_details(self):
        return getattr(self, self.get_details_model(self.contract_type).__name__.lower()+'_set').first()

    @classmethod
    def get_details_model(self, contract_type):
        return contract_details_types[contract_type]['model']

'''
real contract to deploy to ethereum
'''
class EthContract(models.Model):
    contract = models.ForeignKey(Contract, null=True, default=None)
    address = models.CharField(max_length=50, null=True, default=None)
    source_code = models.TextField()
    bytecode = models.TextField()
    abi = JSONField(default={})
    compiler_version = models.CharField(max_length=200, null=True, default=None)


class CommonDetails(models.Model):
    class Meta:
        abstract = True
    contract = models.ForeignKey(Contract)#, related_name='%(class)s')

    def compile(self, sol_path=None, eth_contract_attr_name='eth_contract'):
        sol_path = sol_path or self.sol_path
        if hasattr(self, eth_contract_attr_name):
            getattr(self, eth_contract_attr_name).delete()
        sol_path = path.join(CONTRACTS_DIR, sol_path)
        with open(sol_path) as f:
            source = f.read()
        directory = path.dirname(sol_path)
        result = json.loads(Popen(
                SOLC.format(directory).split(),
                stdin=PIPE,
                stdout=PIPE,
                cwd=directory
        ).communicate(source.encode())[0].decode())
        eth_contract = EthContract()
        eth_contract.source_code = source
        eth_contract.compiler_version = result['version']
        sol_path_name = path.basename(sol_path)[:-4]
        eth_contract.abi = json.loads(result['contracts']['<stdin>:'+sol_path_name]['abi'])
        eth_contract.bytecode = result['contracts']['<stdin>:'+sol_path_name]['bin']
        eth_contract.save()
        setattr(self, eth_contract_attr_name, eth_contract)
        self.save()


    def deploy(self):
        self.compile()
        tr = abi.ContractTranslator(self.eth_contract.abi)
        arguments = self.get_arguments()
        par_int = ParInt()
        nonce = int(par_int.parity_nextNonce(self.owner_address), 16)
        print('nonce', nonce)

        signed_data = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
                'source' : self.owner_address,
                'data': self.bytecode + binascii.hexlify(tr.encode_constructor_arguments(arguments)).decode(),
                'nonce': nonce,
                'gaslimit': self.get_details().get_gaslimit(),
                'value': self.get_details().get_value(),
        }).content.decode())['result']

        par_int.eth_sendRawTransaction('0x' + signed_data)
        print('transaction sent')

        self.contract.state = 'WAITING_FOR_DEPLOYMENT'

        self.contract.save()

    def msg_deployed(message):
        self.eth_contract.address = message['address']
        self.eth_contract.save()
        self.contract.state = 'ACTIVE'
        contract.save()
#        self.contract.get_details().deployed(message)
        if contract.user.email:
            send_mail(
                    'Contract deployed',
                    'Contract deployed message',
                    DEFAULT_FROM_EMAIL,
                    [contract.user.email]
            )

@contract_details('MyWish Original')
class ContractDetailsLastwill(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/LastWillOraclize.sol'

    user_address = models.CharField(max_length=50, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    def get_arguments(self):
        return [
            self.user_address,
            [h.address for h in self.contract.heir_set.all()],
            [h.percentage for h in self.contract.heir_set.all()],
            self.check_interval,
            ORACLIZE_PROXY,
        ]
   

    @staticmethod
    def calc_cost(kwargs):
        heirs_num = int(kwargs['heirs_num']) if 'heirs_num' in kwargs else len(kwargs['heirs'])
        active_to = kwargs['active_to']
        if isinstance(active_to, str):
            active_to = datetime.date(*map(int, active_to.split('-')))
        elif isinstance(active_to, datetime.datetime):
            active_to = active_to.date()
        check_interval = int(kwargs['check_interval'])
        Cg = 780476
        CBg = 26561
        Tg = 22000
        Gp = 20 * 10 ** 9
        Dg = 29435
        DBg = 9646
        B = heirs_num
        Cc = 124852
        DxC = max(abs((datetime.date.today() - active_to).total_seconds() / check_interval), 1)
        O = 25000 * 10 ** 9
        return 2 * int(Tg * Gp + Gp * (Cg + B * CBg) + Gp * (Dg + DBg * B) + (Gp * Cc + O) * DxC)

    def deployed(self, message):
        self.next_check = timezone.now() + datetime.timedelta(seconds=self.check_interval)
        self.save()

    def checked(self, message):
        now = timezone.now()
        self.last_check = now
        next_check = now + datetime.timedelta(seconds=self.check_interval)
        if next_check < self.active_to:
            self.next_check = next_check
        else:
            self.contract.state = 'EXPIRED'
            contract.save()
            self.next_check = None
        self.save()

    def triggered(self, message):
        self.last_check = timezone.now()
        self.next_check = None
        self.save()

    def get_gaslimit(self):
        Cg = 780476
        CBg = 26561
        return Cg + len(self.contract.heir_set.all()) * CBg

    def get_value(self):
        return 0


@contract_details('MyWish Wallet')
class ContractDetailsLostKey(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/LastWillParityWallet.sol'
    user_address = models.CharField(max_length=50, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)
        
    def get_arguments(self):
        return [
            self.user_address,
            [h.address for h in self.contract.heir_set.all()],
            [h.percentage for h in self.contract.heir_set.all()],
            self.check_interval,
        ]   


    @staticmethod
    def calc_cost(kwargs):
        heirs_num = int(kwargs['heirs_num']) if 'heirs_num' in kwargs else len(kwargs['heirs'])
        active_to = kwargs['active_to']
        if isinstance(active_to, str):
            active_to = datetime.date(*map(int, active_to.split('-')))
        elif isinstance(active_to, datetime.datetime):
            active_to = active_to.date()
        check_interval = int(kwargs['check_interval'])
        Cg = 1476117
        CBg = 28031
        Tg = 22000
        Gp = 20 * 10 ** 9
        Dg = 29435
        DBg = 9646
        B = heirs_num
        Cc = 124852
        DxC = max(abs((datetime.date.today() - active_to).total_seconds() / check_interval), 1)
        O = 25000 * 10 ** 9
        return 2 * int(Tg * Gp + Gp * (Cg + B * CBg) + Gp * (Dg + DBg * B) + (Gp * Cc + O) * DxC)

    def deployed(self, message):
        self.next_check = timezone.now() + datetime.timedelta(seconds=self.check_interval)
        self.save()

    def checked(self, message):
        now = timezone.now()
        self.last_check = now
        next_check = now + datetime.timedelta(seconds=self.check_interval)
        if next_check < self.active_to:
            self.next_check = next_check
        else:
            self.contract.state = 'EXPIRED'
            contract.save()
            self.next_check = None
        self.save()

    def triggered(self, message):
        self.last_check = timezone.now()
        self.next_check = None
        self.save()

    def get_gaslimit(self):
        Cg = 1476117
        CBg = 28031
        return Cg + len(self.contract.heir_set.all()) * CBg + 3000

    def get_value(self): 
        return 0


@contract_details('MyWish Delayed Payment')
class ContractDetailsDelayedPayment(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/DelayedPayment.sol'
    date = models.DateTimeField()
    user_address = models.CharField(max_length=50)
    recepient_address = models.CharField(max_length=50)
    recepient_email = models.CharField(max_length=200, null=True)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    @staticmethod
    def calc_cost(kwargs):
        return 25000000000000000

    def deployed(self, message):
        pass

    def checked(self, message):
        pass

    def triggered(self, message):
        pass
    
    def get_arguments(self):
        return [
            self.user_address,
            self.recepient_address,
            2**256 - 1,
            int(self.date.timestamp()),
        ]

    def get_gaslimit(self):
        return 1700000

    def get_value(self): 
        return 0


@contract_details('Pizza')
class ContractDetailsPizza(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/Pizza.sol'
    user_address = models.CharField(max_length=50)
    pizzeria_address = models.CharField(max_length=50, default='0x1eee4c7d88aadec2ab82dd191491d1a9edf21e9a')
    timeout = models.IntegerField(default=60*60)
    code = models.IntegerField()
    salt = models.CharField(max_length=len(str(2**256)))
    pizza_cost = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0) # weis
    order_id = models.DecimalField(max_digits=50, decimal_places=0, unique=True)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    def get_gaslimit(self):
        return 423037 + 5000
    
    @staticmethod
    def calc_cost(kwargs):
        pizza_cost = int(kwargs['pizza_cost'])
        pizza_cost = 1 # for testing
        '''
        Construct: 423037
        Check: 22764
        Hot pizza: 56478
        Check and send: 62716
        Cold pizza: 56467
        '''
        Cg = 423037
        Ch = 22764
        Hp = 56478
        CaS = 62716
        Cp = 56467
        return pizza_cost + 2*(Cg + Ch + max(Hp,Cp) + CaS) * 20000000000

    def get_arguments(self):
        return [
            self.user_address,
            self.pizzeria_address,
            binascii.unhexlify(sha3.keccak_256(int(self.code).to_bytes(32,'big') + int(self.salt).to_bytes(32,'big')).hexdigest().encode()),
            int(self.timeout),
        ]

    def get_value(self): 
        return int(self.pizza_cost)

    def deployed(self, message):
        pass



@contract_details('MyWish ICO')
class ContractDetailsICO(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/ICO.sol'

    soft_cap = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True)
    hard_cap = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True)
    token_name = models.CharField(max_length=512)
    token_short_name = models.CharField(max_length=64)
    admin_address = models.CharField(max_length=50)
    is_transferable_at_once = models.BooleanField(default=False)
    start_date = models.IntegerField()
    stop_date = models.IntegerField()
    rate = models.IntegerField()
    decimals = models.IntegerField()
    platform_as_admin = models.BooleanField(default=False)
    temp_directory = models.CharField(max_length=36)

    eth_contract_token = models.ForeignKey(EthContract, null=True, default=None, related_name='ico_details_token')
    eth_contract_crowdsale = models.ForeignKey(EthContract, null=True, default=None, related_name='ico_details_crowdsale')

    def calc_cost(self):
        return 10**18

    def compile(self):
        temp_directory = str(uuid.uuid4())
        os.mkdir(os.path.join(CONTRACTS_TEMP_DIR, temp_directory))
        sour = path.join(CONTRACTS_DIR, 'lastwill/ico-crowdsale/*')
        dest = path.join(CONTRACTS_TEMP_DIR, temp_directory)
        os.system('cp -as {sour} {dest}'.format(sour=sour, dest=dest))
        preproc_config = os.path.join(dest, 'c-preprocessor-config.json')
        os.unlink(preproc_config)
        with open(preproc_config, 'w') as f:
            f.write(json.dumps({"constants": {
                    "D_START_TIME": self.start_date,
                    "D_END_TIME": self.stop_date,
                    "D_SOFT_CAP_ETH": int(self.soft_cap),
                    "D_HARD_CAP_ETH": int(self.hard_cap),
                    "D_RATE": int(self.rate),
                    "D_NAME": self.token_name,
                    "D_SYMBOL": self.token_short_name,
                    "D_DECIMALS": int(self.decimals),
                    "D_COLD_WALLET": self.admin_address,
                    "D_AUTO_FINALISE": self.platform_as_admin,
                    "D_PAUSE_TOKENS": self.is_transferable_at_once,


                    "D_TOKENS_ADDRESS_1": "0x0000001b717aDd3E840343364EC9d971FBa3955C",
                    "D_TOKENS_FREEZE_1": 1539709200,
                    "D_TOKENS_AMOUNT_1": "1000000",

                    "D_TOKENS_ADDRESS_2": "0x0000002b717aDd3E840343364EC9d971FBa3955C",
                    "D_TOKENS_FREEZE_2": 0,
                    "D_TOKENS_AMOUNT_2": "2000000",

                    "D_TOKENS_ADDRESS_3": "0x0000003b717aDd3E840343364EC9d971FBa3955C",
                    "D_TOKENS_FREEZE_3": 1539709200,
                    "D_TOKENS_AMOUNT_3": "3000000"

            }}))
        os.system('cd {dest} && ./compile.sh'.format(dest=dest))
        eth_contract_crowdsale = EthContract()
        with open(path.join(dest, 'build/contracts/MainCrowdsale.json')) as f:
            crowdsale_json = json.loads(f.read())
        eth_contract_crowdsale.abi = crowdsale_json['abi']
        eth_contract_crowdsale.bytecode = crowdsale_json['bytecode']
        eth_contract_crowdsale.compiler_version = crowdsale_json['compiler']['version']
        eth_contract_crowdsale.source = crowdsale_json['source']
        eth_contract_crowdsale.contract = self.contract
        eth_contract_crowdsale.save()
        self.eth_contract_crowdsale = eth_contract_crowdsale
        eth_contract_token = EthContract()
        with open(path.join(dest, 'build/contracts/MainToken.json')) as f:
            token_json = json.loads(f.read())
        eth_contract_token.abi = crowdsale_json['abi']
        eth_contract_token.bytecode = crowdsale_json['bytecode']
        eth_contract_token.compiler_version = crowdsale_json['compiler']['version']
        eth_contract_token.source = crowdsale_json['source']
        eth_contract_token.contract = self.contract
        eth_contract_token.save()
        self.eth_contract_token = eth_contract_token
        self.save()
#        shutil.rmtree(dest)

class Heir(models.Model):
    contract = models.ForeignKey(Contract)
    address = models.CharField(max_length=50)
    percentage = models.IntegerField()
    email = models.CharField(max_length=200, null=True)


class TokenHolder(models.Model):
    contract = models.ForeignKey(Contract)
    name = models.CharField(max_length=512, null=True)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True)
    freeze_date = models.IntegerField(null=True)

