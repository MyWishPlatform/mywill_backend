from subprocess import Popen, PIPE
from os import path
import requests
import json
import binascii
import sha3
import datetime
from ethereum import abi
from django.db import models
from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from lastwill.settings import ORACLIZE_PROXY, SIGNER
from lastwill.parint import *
from lastwill.contracts.types import contract_types
import lastwill.check as check

MAX_WEI_DIGITS = len(str(2**256))

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


    def compile(self):
        sol_path = self.get_details().sol_path
        with open(sol_path) as f:
            source = f.read()
        directory = path.dirname(sol_path)
        result = json.loads(Popen(
                'solc --optimize --combined-json abi,bin --allow-paths={}'.format(directory).split(),
                stdin=PIPE,
                stdout=PIPE,
                cwd=directory
        ).communicate(source.encode())[0].decode())
        self.source_code = source
        self.compiler_version = result['version']
        sol_path_name = path.basename(sol_path)[:-4]
        self.abi = json.loads(result['contracts']['<stdin>:'+sol_path_name]['abi'])
        self.bytecode = result['contracts']['<stdin>:'+sol_path_name]['bin']

    def deploy(self):
        self.compile()
        tr = abi.ContractTranslator(self.abi)
        arguments = self.get_details().get_arguments()
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
        print('signed_data', signed_data)

        par_int.eth_sendRawTransaction('0x' + signed_data)

        self.state = 'WAITING_FOR_DEPLOYMENT'

        self.save()

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
        return getattr(self, self.get_details_model(self.contract_type).related_name).first()

    @classmethod
    def get_details_model(self, contract_type):
        return [ 
                ContractDetailsLastwill,
                ContractDetailsLostKey,
                ContractDetailsDelayedPayment,
                ContractDetailsPizza,
        ][contract_type]


class ContractDetailsLastwill(models.Model):
    sol_path = '/var/www/contracts_repos/lastwill/contracts/contracts/LastWillOraclize.sol'
    related_name = 'details_lastwill'

    contract = models.ForeignKey(Contract, related_name=related_name)
    user_address = models.CharField(max_length=50, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)

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


class ContractDetailsLostKey(models.Model):
    sol_path = '/var/www/contracts_repos/lastwill/contracts/contracts/LastWillParityWallet.sol'
    related_name = 'details_lostkey'
    
    contract = models.ForeignKey(Contract, related_name=related_name)
    user_address = models.CharField(max_length=50, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
        
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


class ContractDetailsDelayedPayment(models.Model):
    sol_path = '/var/www/contracts_repos/lastwill/contracts/contracts/DelayedPayment.sol'
    related_name = 'details_delayed_payment'

    contract = models.ForeignKey(Contract, related_name=related_name)
    date = models.DateTimeField()
    user_address = models.CharField(max_length=50)
    recepient_address = models.CharField(max_length=50)
    recepient_email = models.CharField(max_length=200, null=True)

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


class ContractDetailsPizza(models.Model):
    sol_path = '/var/www/contracts_repos/lastwill/contracts/contracts/Pizza.sol'
    related_name = 'details_pizza'

    contract = models.ForeignKey(Contract, related_name=related_name)
    user_address = models.CharField(max_length=50)
    pizzeria_address = models.CharField(max_length=50, default='0x1eee4c7d88aadec2ab82dd191491d1a9edf21e9a')
    timeout = models.IntegerField(default=60*60)
    code = models.IntegerField()
    salt = models.CharField(max_length=len(str(2**256)))
    pizza_cost = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0) # weis
    order_id = models.DecimalField(max_digits=50, decimal_places=0, unique=True)

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


class Heir(models.Model):
    contract = models.ForeignKey(Contract)
    address = models.CharField(max_length=50)
    percentage = models.IntegerField()
    email = models.CharField(max_length=200, null=True)


