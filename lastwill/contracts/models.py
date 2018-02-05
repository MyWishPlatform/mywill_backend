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
from copy import deepcopy
from time import sleep
from ethereum import abi
from django.db import models
from django.db.models import Q
from django.core.mail import send_mail
from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from lastwill.settings import ORACLIZE_PROXY, SIGNER, SOLC, CONTRACTS_DIR, CONTRACTS_TEMP_DIR, DEPLOY_ADDR, DEFAULT_FROM_EMAIL
from lastwill.parint import *
import lastwill.check as check
from lastwill.consts import MAX_WEI_DIGITS
from lastwill.deploy.models import DeployAddress

contract_details_types = []

def contract_details(name):
    def w(c):
        contract_details_types.append({
                'name': name,
                'model': c,
        })
        return c
    return w

class NeedRequeue(Exception):
    pass

class TxFail(Exception):
    pass

class AlreadyPostponed(Exception):
    pass


def check_transaction(f):
    def wrapper(*args, **kwargs):
        if not args[1].get('success', True):
            print('message rejected because deploy failed', flush=True)
            raise TxFail()
        else:
            return f(*args, **kwargs)
    return wrapper

def postponable(f):
    def wrapper(*args, **kwargs):
        contract = args[0].contract
        if contract.state == 'POSTPONED':
            print('message rejected because contract postponed', flush=True)
            raise AlreadyPostponed
        try:
            return f(*args, **kwargs)
        except Exception as e:
            print('contract postponed due to exception', flush=True)
            contract.state = 'POSTPONED'
            contract.save()
            raise
    return wrapper

def blocking(f):
    def wrapper(*args, **kwargs):
        if not DeployAddress.objects.select_for_update().filter(
                Q(address=DEPLOY_ADDR) & (Q(locked_by__isnull=True) | Q(locked_by=args[0].contract.id))
        ).update(locked_by=args[0].contract.id):
            print('address locked. sleeping 5 and requeueing the message', flush=True)
            sleep(5)
            raise NeedRequeue()
        else:
            try:
                return f(*args, **kwargs)
            except:
                print('releasing lock due to exception', flush=True)
                DeployAddress.objects.select_for_update().filter(address=DEPLOY_ADDR).update(locked_by=None)
                raise
    return wrapper

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
    tx_hash = models.CharField(max_length=70, null=True, default=None)


class CommonDetails(models.Model):
    class Meta:
        abstract = True
    contract = models.ForeignKey(Contract)#, related_name='%(class)s')

    def compile(self, eth_contract_attr_name='eth_contract'):
        print('compiling', flush=True)
        sol_path = self.sol_path
        if getattr(self, eth_contract_attr_name):
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
        eth_contract.contract = self.contract
        eth_contract.save()
        setattr(self, eth_contract_attr_name, eth_contract)
        self.save()

    @blocking
    @postponable
    def deploy(self, eth_contract_attr_name='eth_contract'):
        self.compile(eth_contract_attr_name)
        eth_contract = getattr(self, eth_contract_attr_name)
        tr = abi.ContractTranslator(eth_contract.abi)
        arguments = self.get_arguments(eth_contract_attr_name)
        print('arguments', arguments)
        par_int = ParInt()
        nonce = int(par_int.parity_nextNonce(DEPLOY_ADDR), 16)
        print('nonce', nonce)
        signed_data = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
                'source' : DEPLOY_ADDR,
                'data': eth_contract.bytecode + (binascii.hexlify(tr.encode_constructor_arguments(arguments)).decode() if arguments else ''),
                'nonce': nonce,
                'gaslimit': self.get_gaslimit(),
                'value': self.get_value(),
        }).content.decode())['result']

        eth_contract.tx_hash = par_int.eth_sendRawTransaction('0x' + signed_data)
        eth_contract.save()
        print('transaction sent')

        self.contract.state = 'WAITING_FOR_DEPLOYMENT'

        self.contract.save()
    
    def msg_deployed(self, message):
        DeployAddress.objects.select_for_update().filter(address=DEPLOY_ADDR).update(locked_by=None)
        self.eth_contract.address = message['address']
        self.eth_contract.save()
        self.contract.state = 'ACTIVE'
        self.contract.save()
        if self.contract.user.email:
            send_mail(
                    'Contract deployed',
                    'Contract deployed message',
                    DEFAULT_FROM_EMAIL,
                    [self.contract.user.email]
            )

    def get_value(self): 
        return 0


@contract_details('MyWish Original')
class ContractDetailsLastwill(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/LastWillOraclize.sol'

    user_address = models.CharField(max_length=50, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    def get_arguments(self, *args, **kwargs):
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
        return 2 * int(Tg * Gp + Gp * (Cg + B * CBg) + Gp * (Dg + DBg * B) + (Gp * Cc + O) * DxC)     + 80000

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        super().msg_deployed(message)
        self.next_check = timezone.now() + datetime.timedelta(seconds=self.check_interval)
        self.save()

    @check_transaction
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

    @check_transaction
    def triggered(self, message):
        self.last_check = timezone.now()
        self.next_check = None
        self.save()

    def get_gaslimit(self):
        Cg = 780476
        CBg = 26561
        return Cg + len(self.contract.heir_set.all()) * CBg + 80000



@contract_details('MyWish Wallet')
class ContractDetailsLostKey(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/LastWillParityWallet.sol'
    user_address = models.CharField(max_length=50, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)
        
    def get_arguments(self, *args, **kwargs):
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
        return 2 * int(Tg * Gp + Gp * (Cg + B * CBg) + Gp * (Dg + DBg * B) + (Gp * Cc + O) * DxC) + 80000

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        super().msg_deployed(message)
        self.next_check = timezone.now() + datetime.timedelta(seconds=self.check_interval)
        self.save()

    @check_transaction
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

    @check_transaction
    def triggered(self, message):
        self.last_check = timezone.now()
        self.next_check = None
        self.save()

    def get_gaslimit(self):
        Cg = 1476117
        CBg = 28031
        return Cg + len(self.contract.heir_set.all()) * CBg + 3000 + 80000


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

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        super().msg_deployed(message)

    def checked(self, message):
        pass

    def triggered(self, message):
        pass
    
    def get_arguments(self, *args, **kwargs):
        return [
            self.user_address,
            self.recepient_address,
            2**256 - 1,
            int(self.date.timestamp()),
        ]

    def get_gaslimit(self):
        return 1700000


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

    def get_arguments(self, *args, **kwargs):
        return [
            self.user_address,
            self.pizzeria_address,
            binascii.unhexlify(sha3.keccak_256(int(self.code).to_bytes(32,'big') + int(self.salt).to_bytes(32,'big')).hexdigest().encode()),
            int(self.timeout),
        ]

    def get_value(self): 
        return int(self.pizza_cost)

    def msg_deployed(self, message):
        super().msg_deployed(message)



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
    rate = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True)
    decimals = models.IntegerField()
    platform_as_admin = models.BooleanField(default=False)
    temp_directory = models.CharField(max_length=36)
    time_bonuses = JSONField(null=True, default=None)
    amount_bonuses = JSONField(null=True, default=None)
    continue_minting = models.BooleanField(default=False)

    eth_contract_token = models.ForeignKey(EthContract, null=True, default=None, related_name='ico_details_token', on_delete=models.SET_NULL)
    eth_contract_crowdsale = models.ForeignKey(EthContract, null=True, default=None, related_name='ico_details_crowdsale', on_delete=models.SET_NULL)

    def calc_cost(self):
        return 10**18

    def compile(self, eth_contract_attr_name='eth_contract_token'):
        print('ico_contract compile')
        if self.temp_directory:
            print('already compiled')
            return
        self.temp_directory = str(uuid.uuid4())
        print(self.temp_directory, flush=True)
        sour = path.join(CONTRACTS_DIR, 'lastwill/ico-crowdsale/*')
        dest = path.join(CONTRACTS_TEMP_DIR, self.temp_directory)
        os.mkdir(dest)
        os.system('cp -as {sour} {dest}'.format(sour=sour, dest=dest))
        preproc_config = os.path.join(dest, 'c-preprocessor-config.json')
        os.unlink(preproc_config)
        token_holders = self.contract.tokenholder_set.all()

        amount_bonuses = []
        if self.amount_bonuses:
            curr_min_amount = 0
            for bonus in self.amount_bonuses:
                amount_bonuses.append({
                         'max_amount': bonus['min_amount'],
                         'bonus': bonus['bonus']
                })
                if int(bonus['min_amount']) > curr_min_amount: # fill gap with zero
                    amount_bonuses.append({
                             'max_amount': bonus['max_amount'],
                             'bonus': 0
                    })
                curr_min_amount = int(bonus['max_amount'])


        time_bonuses = deepcopy(self.time_bonuses)
        for bonus in time_bonuses:
            if bonus.get('min_time', None) is None:
                bonus['min_time'] = self.start_date
                bonus['max_time'] = self.stop_date - 5
            else:
                if int(bonus['max_time']) > int(self.stop_date) - 5:
                    bonus['max_time'] = int(self.stop_date) - 5
            if bonus.get('min_amount', None) is None:
                bonus['min_amount'] = 0
                bonus['max_amount'] = self.hard_cap


        preproc_params = {"constants": {
                    "D_START_TIME": self.start_date,
                    "D_END_TIME": self.stop_date,
                    "D_SOFT_CAP_WEI": str(self.soft_cap),
                    "D_HARD_CAP_WEI": str(self.hard_cap),
                    "D_RATE": int(self.rate),
                    "D_NAME": self.token_name,
                    "D_SYMBOL": self.token_short_name,
                    "D_DECIMALS": int(self.decimals),
                    "D_COLD_WALLET": '0x9b37d7b266a41ef130c4625850c8484cf928000d', # self.admin_address,
                    "D_AUTO_FINALISE": self.platform_as_admin,
                    "D_PAUSE_TOKENS": not self.is_transferable_at_once,

                    "D_PREMINT_COUNT": len(token_holders),
                    
                    "D_PREMINT_ADDRESSES": ','.join(map(lambda th: 'address(%s)'%th.address, token_holders)),
                    "D_PREMINT_AMOUNTS": ','.join(map(lambda th: 'uint(%s)'%th.amount, token_holders)),
                    "D_PREMINT_FREEZES": ','.join(map(lambda th: 'uint64(%s)'%(th.freeze_date if th.freeze_date else 0), token_holders)),

                    "D_BONUS_TOKENS": "true" if time_bonuses or amount_bonuses else "false",

                    "D_WEI_RAISED_AND_TIME_BONUS_COUNT": len(time_bonuses),
                    "D_WEI_RAISED_STARTS_BOUNDARIES": ','.join(map(lambda b: 'uint(%s)'%b['min_amount'], time_bonuses)),
                    "D_WEI_RAISED_ENDS_BOUNDARIES": ','.join(map(lambda b: 'uint(%s)'%b['max_amount'], time_bonuses)),
                    "D_TIME_STARTS_BOUNDARIES": ','.join(map(lambda b: 'uint64(%s)'%b['min_time'], time_bonuses)),
                    "D_TIME_ENDS_BOUNDARIES": ','.join(map(lambda b: 'uint64(%s)'%b['max_time'], time_bonuses)),
                    "D_WEI_RAISED_AND_TIME_MILLIRATES": ','.join(map(lambda b: 'uint(%s)'%(int(10*b['bonus'])), time_bonuses)),

                    "D_WEI_AMOUNT_BONUS_COUNT": len(amount_bonuses),
                    "D_WEI_AMOUNT_BOUNDARIES": ','.join(map(lambda b: 'uint(%s)'%b['max_amount'], reversed(amount_bonuses))),
                    "D_WEI_AMOUNT_MILLIRATES": ','.join(map(lambda b: 'uint(%s)'%(int(10*b['bonus'])), reversed(amount_bonuses))),

                    "D_CONTINUE_MINTING": self.continue_minting,
                    "D_MYWISH_ADDRESS": '0xe33c67fcb6f17ecadbc6fa7e9505fc79e9c8a8fd',
        }}
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && ./compile.sh'.format(dest=dest)):
            raise Exception('compiler error while testing')
        if os.system('cd {dest} && ./test.sh'.format(dest=dest)):
            raise Exception('testing error')

        preproc_params['constants']['D_COLD_WALLET'] = self.admin_address
        preproc_params['constants']['D_MYWISH_ADDRESS'] = DEPLOY_ADDR
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && ./compile.sh'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        eth_contract_crowdsale = EthContract()
        with open(path.join(dest, 'build/contracts/TemplateCrowdsale.json')) as f:
            crowdsale_json = json.loads(f.read())
        eth_contract_crowdsale.abi = crowdsale_json['abi']
        eth_contract_crowdsale.bytecode = crowdsale_json['bytecode'][2:]
        eth_contract_crowdsale.compiler_version = crowdsale_json['compiler']['version']
        eth_contract_crowdsale.source_code = crowdsale_json['source']
        eth_contract_crowdsale.contract = self.contract
        eth_contract_crowdsale.save()
        self.eth_contract_crowdsale = eth_contract_crowdsale
        eth_contract_token = EthContract()
        with open(path.join(dest, 'build/contracts/MainToken.json')) as f:
            token_json = json.loads(f.read())
        eth_contract_token.abi = token_json['abi']
        eth_contract_token.bytecode = token_json['bytecode'][2:]
        eth_contract_token.compiler_version = token_json['compiler']['version']
        eth_contract_token.source_code = token_json['source']
        eth_contract_token.contract = self.contract
        eth_contract_token.save()
        self.eth_contract_token = eth_contract_token
        self.save()
#        shutil.rmtree(dest)

    @blocking
    @check_transaction
    @postponable
    def msg_deployed(self, message):
        assert(message['success'])
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            return
        if self.eth_contract_token.id == message['contractId']:
            self.eth_contract_token.address = message['address']
            self.eth_contract_token.save()
            self.deploy(eth_contract_attr_name='eth_contract_crowdsale')
        else:
            self.eth_contract_crowdsale.address = message['address']
            self.eth_contract_crowdsale.save()

            tr = abi.ContractTranslator(self.eth_contract_token.abi)
            par_int = ParInt()
            nonce = int(par_int.parity_nextNonce(DEPLOY_ADDR), 16) 
            print('nonce', nonce)
            response = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
                    'source' : DEPLOY_ADDR,
                    'data': binascii.hexlify(tr.encode_function_call('transferOwnership', [self.eth_contract_crowdsale.address])).decode(),
                    'nonce': nonce,
                    'dest': self.eth_contract_token.address,
                    'gaslimit': 100000,
            }).content.decode())
            print('transferOwnership message signed')
            signed_data = response['result']
            self.eth_contract_token.tx_hash = par_int.eth_sendRawTransaction('0x'+signed_data)
            print('transferOwnership message sended')

    def get_gaslimit(self):
        return 3200000

    @blocking
    @postponable
    def deploy(self, eth_contract_attr_name='eth_contract_token'):
        return super().deploy(eth_contract_attr_name)
        
    def get_arguments(self, eth_contract_attr_name):
        return {
                'eth_contract_token': [],
                'eth_contract_crowdsale': [self.eth_contract_token.address],
        }[eth_contract_attr_name]

    # token
    @blocking
    @check_transaction
    @postponable
    def ownershipTransferred(self, message):
        if message['contractId'] != self.eth_contract_token.id:
            if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
                DeployAddress.objects.select_for_update().filter(address=DEPLOY_ADDR).update(locked_by=None)
            print('ignored', flush=True)
            return
        tr = abi.ContractTranslator(self.eth_contract_crowdsale.abi)
        par_int = ParInt()
        nonce = int(par_int.parity_nextNonce(DEPLOY_ADDR), 16)
        print('nonce', nonce)
        response = json.loads(requests.post('http://{}/sign/'.format(SIGNER), json={
                'source' : DEPLOY_ADDR,
                'data': binascii.hexlify(tr.encode_function_call('init', [])).decode(),
                'nonce': nonce,
                'dest': self.eth_contract_crowdsale.address,
                'gaslimit': 100000 + 50000 * self.contract.tokenholder_set.all().count(),
        }).content.decode())
        print('init message signed')
        signed_data = response['result']
        self.eth_contract_crowdsale.tx_hash = par_int.eth_sendRawTransaction('0x'+signed_data)
        print('init message sended')


    # crowdsale
    @check_transaction
    @postponable
    def initialized(self, message):
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            return
        DeployAddress.objects.select_for_update().filter(address=DEPLOY_ADDR).update(locked_by=None)
        if message['contractId'] != self.eth_contract_crowdsale.id:
            print('ignored', flush=True)
            return
        self.contract.state = 'ACTIVE'
        self.contract.save()
        if self.contract.user.email:
            send_mail(
                    'Contract deployed',
                    'Contract deployed message',
                    DEFAULT_FROM_EMAIL,
                    [self.contract.user.email]
            )


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

