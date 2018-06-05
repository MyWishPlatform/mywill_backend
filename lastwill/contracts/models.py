from subprocess import Popen, PIPE
from os import path
import os
import uuid
import binascii
import datetime
import pika
import math
import bitcoin
from copy import deepcopy
from ethereum import abi

from django.db import models
from django.db.models import F
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from neo.Core.TX.Transaction import ContractTransaction
from neocore.IO.BinaryWriter import BinaryWriter
from neo.SmartContract.ContractParameterType import ContractParameterType
from neo.IO.MemoryStream import StreamManager
from neo.Core.Witness import Witness
from neocore.Cryptography.Crypto import Crypto
from neocore.UInt160 import UInt160


from lastwill.settings import SIGNER, SOLC, CONTRACTS_DIR, CONTRACTS_TEMP_DIR
from lastwill.settings import test_logger
from lastwill.parint import *
from lastwill.consts import MAX_WEI_DIGITS, MAIL_NETWORK
from lastwill.deploy.models import DeployAddress, Network
from lastwill.contracts.decorators import *
from email_messages import *


def add_token_params(params, details, token_holders, pause, cont_mint):
    params["D_ERC"] = details.token_type
    params["D_NAME"] = details.token_name
    params["D_SYMBOL"] = details.token_short_name
    params["D_DECIMALS"] = details.decimals
    params["D_CONTINUE_MINTING"] = cont_mint
    params["D_CONTRACTS_OWNER"] = "0x8ffff2c69f000c790809f6b8f9abfcbaab46b322"
    params["D_PAUSE_TOKENS"] = pause
    params["D_PREMINT_COUNT"] = len(token_holders)
    params["D_PREMINT_ADDRESSES"] = ','.join(map(
        lambda th: 'address(%s)' % th.address, token_holders
    ))
    params["D_PREMINT_AMOUNTS"] = ','.join(map(
        lambda th: 'uint(%s)' % th.amount, token_holders
    ))
    params["D_PREMINT_FREEZES"] = ','.join(map(
        lambda th: 'uint64(%s)' % (
            th.freeze_date if th.freeze_date else 0
        ), token_holders
    ))
    return params


def add_crowdsale_params(params, details, time_bonuses, amount_bonuses):
    params["D_START_TIME"] = details.start_date
    params["D_END_TIME"] = details.stop_date
    params["D_SOFT_CAP_WEI"] = str(details.soft_cap)
    params["D_HARD_CAP_WEI"] = str(details.hard_cap)
    params["D_RATE"] = int(details.rate)
    params["D_COLD_WALLET"] = '0x9b37d7b266a41ef130c4625850c8484cf928000d'
    params["D_CONTRACTS_OWNER"] = '0x8ffff2c69f000c790809f6b8f9abfcbaab46b322'
    params["D_AUTO_FINALISE"] = details.platform_as_admin
    params["D_BONUS_TOKENS"] = "true" if time_bonuses or amount_bonuses else "false"
    params["D_WEI_RAISED_AND_TIME_BONUS_COUNT"] = len(time_bonuses)
    params["D_WEI_RAISED_STARTS_BOUNDARIES"] = ','.join(
        map(lambda b: 'uint(%s)' % b['min_amount'], time_bonuses))
    params["D_WEI_RAISED_ENDS_BOUNDARIES"] = ','.join(
        map(lambda b: 'uint(%s)' % b['max_amount'], time_bonuses))
    params["D_TIME_STARTS_BOUNDARIES"] = ','.join(
        map(lambda b: 'uint64(%s)' % b['min_time'], time_bonuses))
    params["D_TIME_ENDS_BOUNDARIES"] = ','.join(
        map(lambda b: 'uint64(%s)' % b['max_time'], time_bonuses))
    params["D_WEI_RAISED_AND_TIME_MILLIRATES"] = ','.join(
        map(lambda b: 'uint(%s)' % (int(10 * b['bonus'])), time_bonuses))
    params["D_WEI_AMOUNT_BONUS_COUNT"] = len(amount_bonuses)
    params["D_WEI_AMOUNT_BOUNDARIES"] = ','.join(
        map(lambda b: 'uint(%s)' % b['max_amount'], reversed(amount_bonuses)))
    params["D_WEI_AMOUNT_MILLIRATES"] = ','.join(
        map(lambda b: 'uint(%s)' % (int(10 * b['bonus'])),
            reversed(amount_bonuses)))
    params["D_MYWISH_ADDRESS"] = '0xe33c67fcb6f17ecadbc6fa7e9505fc79e9c8a8fd'
    return params


def add_amount_bonuses(details):
    amount_bonuses = []
    if details.amount_bonuses:
        curr_min_amount = 0
        for bonus in details.amount_bonuses:
            amount_bonuses.append({
                'max_amount': bonus['min_amount'],
                'bonus': bonus['bonus']
            })
            if int(bonus[
                       'min_amount']) > curr_min_amount:  # fill gap with zero
                amount_bonuses.append({
                    'max_amount': bonus['max_amount'],
                    'bonus': 0
                })
            curr_min_amount = int(bonus['max_amount'])
    return amount_bonuses


def add_time_bonuses(details):
    time_bonuses = deepcopy(details.time_bonuses)
    for bonus in time_bonuses:
        if bonus.get('min_time', None) is None:
            bonus['min_time'] = details.start_date
            bonus['max_time'] = details.stop_date - 5
        else:
            if int(bonus['max_time']) > int(details.stop_date) - 5:
                bonus['max_time'] = int(details.stop_date) - 5
        if bonus.get('min_amount', None) is None:
            bonus['min_amount'] = 0
            bonus['max_amount'] = details.hard_cap
    return time_bonuses


def create_ethcontract_in_compile(abi, bytecode, cv, contract, source_code):
    eth_contract_token = EthContract()
    eth_contract_token.abi = abi
    eth_contract_token.bytecode = bytecode
    eth_contract_token.compiler_version = cv
    eth_contract_token.contract = contract
    eth_contract_token.original_contract = contract
    eth_contract_token.source_code = source_code
    eth_contract_token.save()
    return eth_contract_token


def add_real_params(params, admin_address, address, wallet_address):
    params['constants']['D_CONTRACTS_OWNER'] = admin_address
    params['constants']['D_MYWISH_ADDRESS'] = address
    params['constants']['D_COLD_WALLET'] = wallet_address
    return params


def create_directory(details, sour_path='lastwill/ico-crowdsale/*', config_name='c-preprocessor-config.json'):
    details.temp_directory = str(uuid.uuid4())
    test_logger.info('temp directory = %s' % details.temp_directory)
    print(details.temp_directory, flush=True)
    sour = path.join(CONTRACTS_DIR, sour_path)
    dest = path.join(CONTRACTS_TEMP_DIR, details.temp_directory)
    os.mkdir(dest)
    os.system('cp -as {sour} {dest}'.format(sour=sour, dest=dest))
    preproc_config = os.path.join(dest, config_name)
    os.unlink(preproc_config)
    details.save()
    return dest, preproc_config


def test_crowdsale_params(config, params, dest):
    with open(config, 'w') as f:
        f.write(json.dumps(params))
    if os.system("/bin/bash -c 'cd {dest} && ./compile-crowdsale.sh'".format(
            dest=dest)):
        raise Exception('compiler error while testing')
    if os.system("/bin/bash -c 'cd {dest} && ./test-crowdsale.sh'".format(
            dest=dest)):
        raise Exception('testing error')


def test_token_params(config, params, dest):
    with open(config, 'w') as f:
        f.write(json.dumps(params))
    if os.system("/bin/bash -c 'cd {dest} && ./compile-token.sh'".format(dest=dest)):
        raise Exception('compiler error while deploying')


def test_neo_token_params(config, params, dest):
    with open(config, 'w') as f:
        f.write(json.dumps(params))
    if os.system("/bin/bash -c 'cd {dest} && ./3_test_token.sh'".format(dest=dest)):
        raise Exception('compiler error while deploying')


def test_neo_ico_params(config, params, dest):
    with open(config, 'w') as f:
        f.write(json.dumps(params))
    if os.system("/bin/bash -c 'cd {dest} && ./3_test_crowdsale.sh'".format(dest=dest)):
        raise Exception('compiler error while deploying')


def take_off_blocking(network, contract_id=None, address=None):
    if not address:
        address = NETWORKS[network]['address']
    if not contract_id:
        DeployAddress.objects.select_for_update().filter(
            network__name=network, address=address
        ).update(locked_by=None)
    else:
        DeployAddress.objects.select_for_update().filter(
            network__name=network, address=address, locked_by=contract_id
        ).update(locked_by=None)


def send_in_queue(contract_id, type, queue):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        'localhost',
        5672,
        'mywill',
        pika.PlainCredentials('java', 'java'),
    ))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True, auto_delete=False,
                          exclusive=False)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps({'status': 'COMMITTED', 'contractId': contract_id}),
        properties=pika.BasicProperties(type=type),
    )
    connection.close()


def sign_transaction(address, nonce, gaslimit, network, value=None, dest=None, contract_data=None, gas_price=None):
    data = {
        'source': address,
        'nonce': nonce,
        'gaslimit': gaslimit,
        'network': network,
    }
    if value:
        data['value'] = value
    if dest:
        data['dest'] = dest
    if contract_data:
        data['data'] = contract_data
    if gas_price:
        data['gas_price'] = gas_price

    signed_data = json.loads(requests.post(
        'http://{}/sign/'.format(SIGNER), json=data
    ).content.decode())
    return signed_data['result']


def sign_neo_transaction(tx, binary_tx, address):
    scripts = requests.post(
        'http://{}/neo_sign/'.format(SIGNER),
        json={'binary_tx': binary_tx, 'address': address}
    ).json()
    tx.scripts = [Witness(
        x['invocation'].encode(),
        x['verification'].encode(),
    ) for x in scripts]
    return tx


'''
contract as user see it at site. contract as service. can contain more then one real ethereum contracts
'''


class Contract(models.Model):
    user = models.ForeignKey(User)
    network = models.ForeignKey(Network, default=1)

    address = models.CharField(max_length=50, null=True, default=None)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    user_address = models.CharField(max_length=50, null=True, default=None)

    balance = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True, default=None
    )
    cost = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)

    name = models.CharField(max_length=200, null=True, default=None)
    state = models.CharField(max_length=63, default='CREATED')
    contract_type = models.IntegerField(default=0)

    source_code = models.TextField()
    bytecode = models.TextField()
    abi = JSONField(default={})
    compiler_version = models.CharField(
        max_length=200, null=True, default=None
    )

    created_date = models.DateTimeField(auto_now=True)
    check_interval = models.IntegerField(null=True, default=None)
    active_to = models.DateTimeField(null=True, default=None)
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)

    def save(self, *args, **kwargs):
        # disable balance saving to prevent collisions with java daemon
        print(args)
        str_args = ','.join([str(x) for x in args])
        test_logger.info('class Contract, method save, args: ' + str_args)
        if self.id:
            kwargs['update_fields'] = list(
                    {f.name for f in Contract._meta.fields if f.name not in ('balance', 'id')}
                    &
                    set(kwargs.get('update_fields', [f.name for f in Contract._meta.fields]))
            )
        return super().save(*args, **kwargs)

    def get_details(self):
        return getattr(self, self.get_details_model(
            self.contract_type
        ).__name__.lower()+'_set').first()

    @classmethod
    def get_details_model(self, contract_type):
        return contract_details_types[contract_type]['model']


class BtcKey4RSK(models.Model):
    btc_address = models.CharField(max_length=100, null=True, default=None)
    private_key = models.CharField(max_length=100, null=True, default=None)

'''
real contract to deploy to ethereum
'''


class EthContract(models.Model):
    contract = models.ForeignKey(Contract, null=True, default=None)
    original_contract = models.ForeignKey(
        Contract, null=True, default=None, related_name='orig_ethcontract'
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


class CommonDetails(models.Model):
    class Meta:
        abstract = True
    contract = models.ForeignKey(Contract)

    def compile(self, eth_contract_attr_name='eth_contract'):
        test_logger.info('class details, method compile')
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
        eth_contract.abi = json.loads(
            result['contracts']['<stdin>:'+sol_path_name]['abi']
        )
        eth_contract.bytecode = result['contracts']['<stdin>:'+sol_path_name]['bin']
        eth_contract.contract = self.contract
        eth_contract.original_contract = self.contract
        eth_contract.save()
        setattr(self, eth_contract_attr_name, eth_contract)
        self.save()

    def deploy(self, eth_contract_attr_name='eth_contract'):
        test_logger.info('deploy:')
        if self.contract.state == 'ACTIVE':
            test_logger.error('launch message ignored because already deployed')
            print('launch message ignored because already deployed', flush=True)
            take_off_blocking(self.contract.network.name)
            return
        self.compile(eth_contract_attr_name)
        eth_contract = getattr(self, eth_contract_attr_name)
        tr = abi.ContractTranslator(eth_contract.abi)
        arguments = self.get_arguments(eth_contract_attr_name)
        print('arguments', arguments, flush=True)
        str_args = ','.join([str(x) for x in arguments])
        test_logger.info('class details, method deploy, args: %s' %str_args)
        eth_contract.constructor_arguments = binascii.hexlify(
            tr.encode_constructor_arguments(arguments)
        ).decode() if arguments else ''
        par_int = ParInt(self.contract.network.name)
        address = NETWORKS[self.contract.network.name]['address']
        nonce = int(par_int.eth_getTransactionCount(address, "pending"), 16)
        eth_contract.constructor_arguments = binascii.hexlify(
            tr.encode_constructor_arguments(arguments)
        ).decode() if arguments else ''
        test_logger.info('nonce %d' %nonce)
        print('nonce', nonce, flush=True)
        data = eth_contract.bytecode + (binascii.hexlify(
            tr.encode_constructor_arguments(arguments)
        ).decode() if arguments else '')
        signed_data = sign_transaction(
            address, nonce, self.get_gaslimit(),
            self.contract.network.name, value=self.get_value(),
            contract_data=data
        )
        test_logger.info('source address %s' %address)
        test_logger.info('gas limit %d' %self.get_gaslimit())
        test_logger.info('value %d' %self.get_value())
        test_logger.info('network %s' %self.contract.network.name)
        print('fields of transaction', flush=True)
        print('source', address, flush=True)
        print('gas limit', self.get_gaslimit(), flush=True)
        print('value', self.get_value(), flush=True)
        print('network', self.contract.network.name, flush=True)
        eth_contract.tx_hash = par_int.eth_sendRawTransaction(
            '0x' + signed_data
        )
        eth_contract.save()
        print('transaction sent', flush=True)
        test_logger.info('transaction sent')
        self.contract.state = 'WAITING_FOR_DEPLOYMENT'
        self.contract.save()

    def msg_deployed(self, message, eth_contract_attr_name='eth_contract'):
        network_link = NETWORKS[self.contract.network.name]['link_address']
        network = self.contract.network.name
        network_name = MAIL_NETWORK[network]
        take_off_blocking(self.contract.network.name)
        eth_contract = getattr(self, eth_contract_attr_name)
        eth_contract.address = message['address']
        eth_contract.save()
        self.contract.state = 'ACTIVE'
        self.contract.save()
        if self.contract.user.email:
            send_mail(
                    common_subject,
                    common_text.format(
                        contract_type_name=contract_details_types[self.contract.contract_type]['name'],
                        link=network_link.format(address=eth_contract.address),
                        network_name=network_name
                    ),
                    DEFAULT_FROM_EMAIL,
                    [self.contract.user.email]
            )

    def get_value(self): 
        return 0

    def tx_failed(self, message):
        self.contract.state = 'POSTPONED'
        self.contract.save()
        send_mail(
            postponed_subject,
            postponed_message.format(
                contract_id=self.contract.id
            ),
            DEFAULT_FROM_EMAIL,
            [EMAIL_FOR_POSTPONED_MESSAGE]
        )
        test_logger.error('contract postponed due to transaction fail')
        print('contract postponed due to transaction fail', flush=True)
        take_off_blocking(self.contract.network.name, self.contract.id)
        print('queue unlocked due to transaction fail', flush=True)
        test_logger.error('queue unlocked due to transaction fail')

    def predeploy_validate(self):
        pass

    @blocking
    def check_contract(self):
        print('checking', self.contract.name)
        test_logger.info('checking id %d' %self.id)
        tr = abi.ContractTranslator(self.eth_contract.abi)
        par_int = ParInt(self.contract.network.name)
        address = self.contract.network.deployaddress_set.all()[0].address
        nonce = int(par_int.eth_getTransactionCount(address, "pending"), 16)
        print('nonce', nonce)
        test_logger.info('nonce = %d' %nonce)
        signed_data = sign_transaction(
            address, nonce, 600000, self.contract.network.name,
            dest=self.eth_contract.address,
            contract_data=binascii.hexlify(
                tr.encode_function_call('check', [])
            ).decode(),
        )
        test_logger.info('signed_data %s' %signed_data)
        print('signed_data', signed_data)
        par_int.eth_sendRawTransaction('0x' + signed_data)
        test_logger.info('check ok!')
        print('check ok!')


@contract_details('Will contract')
class ContractDetailsLastwill(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/LastWillNotify.sol'

    user_address = models.CharField(max_length=50, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)
    email = models.CharField(max_length=256, null=True, default=None)
    btc_key = models.ForeignKey(BtcKey4RSK, null=True, default=None)
    platform_alive = models.BooleanField(default=False)
    platform_cancel = models.BooleanField(default=False)
    last_reset = models.DateTimeField(null=True, default=None)
    last_press_imalive = models.DateTimeField(null=True, default=None)
    btc_duty = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=0
    )

    def predeploy_validate(self):
        now = timezone.now()
        if self.active_to < now:
            raise ValidationError({'result': 1}, code=400)

    def contractPayment(self, message):
        if self.contract.network.name not in ['RSK_MAINNET', 'RSK_TESTNET']:
            return
        ContractDetailsLastwill.objects.select_for_update().filter(
            id=self.id
        ).update(btc_duty=F('btc_duty') + message['value'])
        queues = {
            'RSK_MAINNET': 'notification-rsk-fgw',
            'RSK_TESTNET': 'notification-rsk-testnet-fgw'
        }
        queue = queues[self.contract.network.name]
        send_in_queue(self.contract.id, 'make_payment', queue)

    @blocking
    def make_payment(self, message):
        contract = self.contract
        par_int = ParInt(contract.network.name)
        wl_address = NETWORKS[self.contract.network.name]['address']
        balance = int(par_int.eth_getBalance(wl_address), 16)
        gas_limit = 50000
        gas_price = 10 ** 9
        if balance < contract.get_details().btc_duty + gas_limit * gas_price:
            send_mail(
                'RSK',
                'No RSK funds ' + contract.network.name,
                DEFAULT_FROM_EMAIL,
                [EMAIL_FOR_POSTPONED_MESSAGE]
            )
            return
        nonce = int(par_int.eth_getTransactionCount(wl_address, "pending"), 16)
        signed_data = sign_transaction(
            wl_address, nonce, gas_limit, self.contract.network.name,
            value=int(contract.get_details().btc_duty),
            dest=contract.get_details().eth_contract.address,
            gas_price=gas_price
        )
        self.eth_contract.tx_hash = par_int.eth_sendRawTransaction(
            '0x' + signed_data)
        self.eth_contract.save()

    def get_arguments(self, *args, **kwargs):
        return [
            self.user_address,
            [h.address for h in self.contract.heir_set.all()],
            [h.percentage for h in self.contract.heir_set.all()],
            self.check_interval,
            False if self.contract.network.name in
                     ['ETHEREUM_MAINNET', 'ETHEREUM_ROPSTEN'] else True,
        ]

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='ETHEREUM_MAINNET')
        now = datetime.datetime.now()
        cost = cls.calc_cost({
            'check_interval': 1,
            'heirs': [],
            'active_to': now
        }, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        heirs_num = int(kwargs['heirs_num']) if 'heirs_num' in kwargs else len(kwargs['heirs'])
        active_to = kwargs['active_to']
        if isinstance(active_to, str):
            if 'T' in active_to:
                active_to = active_to[:active_to.index('T')]
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
        DxC = max(abs(
            (datetime.date.today() - active_to).total_seconds() / check_interval
        ), 1)
        O = 25000 * 10 ** 9
        result = 2 * int(
            Tg * Gp + Gp * (Cg + B * CBg) + Gp * (Dg + DBg * B) + (Gp * Cc + O) * DxC
        ) + 80000
        if network.name == 'RSK_MAINNET':
            result += 2 * (10 ** 18)
        return result

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
            self.next_check = None
        self.save()
        take_off_blocking(self.contract.network.name, self.contract.id)

    @check_transaction
    def triggered(self, message):
        self.last_check = timezone.now()
        self.next_check = None
        self.save()
        heirs = Heir.objects.filter(contract=self.contract)
        link = NETWORKS[self.eth_contract.contract.network.name]['link_tx']
        for heir in heirs:
            if heir.email:
                send_mail(
                    heir_subject,
                    heir_message.format(
                            user_address=heir.address,
                            link_tx=link.format(tx=message['transactionHash'])
                    ),
                    DEFAULT_FROM_EMAIL,
                    [heir.email]
                )
        self.contract.state = 'TRIGGERED'
        self.contract.save()
        if self.contract.user.email:
            send_mail(
                carry_out_subject, carry_out_message,
                DEFAULT_FROM_EMAIL, [self.contract.user.email]
            )

    def get_gaslimit(self):
        Cg = 780476
        CBg = 26561
        return Cg + len(self.contract.heir_set.all()) * CBg + 80000

    @blocking
    @postponable
    def deploy(self):
        if self.contract.network.name in ['RSK_MAINNET', 'RSK_TESTNET'] and self.btc_key is None:
            priv = os.urandom(32)
            if self.contract.network.name == 'RSK_MAINNET':
                address = bitcoin.privkey_to_address(priv, magicbyte=0)
            else:
                address = bitcoin.privkey_to_address(priv, magicbyte=0x6F)
            btc_key = BtcKey4RSK(
                private_key=binascii.hexlify(priv).decode(),
                btc_address=address
            )
            btc_key.save()
            self.btc_key = btc_key
            self.save()
        super().deploy()

    @blocking
    def i_am_alive(self, message):
        if self.last_press_imalive:
            delta = self.last_press_imalive - timezone.now()
            if delta.days < 1 and delta.total_seconds() < 60 * 60 * 24:
                take_off_blocking(
                    self.contract.network.name, address=self.contract.address
                )
        tr = abi.ContractTranslator(self.eth_contract.abi)
        par_int = ParInt(self.contract.network.name)
        address = self.contract.network.deployaddress_set.all()[0].address
        nonce = int(par_int.eth_getTransactionCount(address, "pending"), 16)
        signed_data = sign_transaction(
            address, nonce, 600000, self.contract.network.name,
            dest=self.eth_contract.address,
            contract_data=binascii.hexlify(
                    tr.encode_function_call('imAvailable', [])
                ).decode(),
        )
        self.eth_contract.tx_hash = par_int.eth_sendRawTransaction(
            '0x' + signed_data
        )
        self.eth_contract.save()
        self.last_press_imalive = timezone.now()

    @blocking
    def cancel(self, message):
        tr = abi.ContractTranslator(self.eth_contract.abi)
        par_int = ParInt(self.contract.network.name)
        address = self.contract.network.deployaddress_set.all()[0].address
        nonce = int(par_int.eth_getTransactionCount(address, "pending"), 16)
        signed_data = sign_transaction(
            address, nonce,  600000, self.contract.network.name,
            dest=self.eth_contract.address,
            contract_data=binascii.hexlify(
                    tr.encode_function_call('kill', [])
                ).decode(),
        )
        self.eth_contract.tx_hash = par_int.eth_sendRawTransaction(
            '0x' + signed_data
        )
        self.eth_contract.save()

    def fundsAdded(self, message):
        if self.contract.network.name not in ['RSK_MAINNET', 'RSK_TESTNET']:
            return
        ContractDetailsLastwill.objects.select_for_update().filter(
            id=self.id
        ).update(btc_duty=F('btc_duty') - message['value'])
        take_off_blocking(self.contract.network.name)


@contract_details('Wallet contract (lost key)')
class ContractDetailsLostKey(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/LastWillParityWallet.sol'
    user_address = models.CharField(max_length=50, null=True, default=None)
    check_interval = models.IntegerField()
    active_to = models.DateTimeField()
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    def predeploy_validate(self):
        now = timezone.now()
        if self.active_to < now:
            raise ValidationError({'result': 1}, code=400)
        
    def get_arguments(self, *args, **kwargs):
        return [
            self.user_address,
            [h.address for h in self.contract.heir_set.all()],
            [h.percentage for h in self.contract.heir_set.all()],
            self.check_interval,
        ]   

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='ETHEREUM_MAINNET')
        now = datetime.datetime.now()
        cost = cls.calc_cost({
            'check_interval': 1,
            'heirs':[],
            'active_to': now
        }, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        heirs_num = int(kwargs['heirs_num']) if 'heirs_num' in kwargs else len(kwargs['heirs'])
        active_to = kwargs['active_to']
        if isinstance(active_to, str):
            if 'T' in active_to:
                active_to = active_to[:active_to.index('T')]
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
        return 2 * int(
            Tg * Gp + Gp * (Cg + B * CBg) + Gp * (Dg + DBg * B) + (Gp * Cc + O) * DxC
        ) + 80000

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
            self.contract.save()
            self.next_check = None
        self.save()
        take_off_blocking(self.contract.network.name, self.contract.id)

    @check_transaction
    def triggered(self, message):
        self.last_check = timezone.now()
        self.next_check = None
        self.save()
        heirs = Heir.objects.filter(contract=self.contract)
        link = NETWORKS[self.eth_contract.contract.network.name]['link_tx']
        for heir in heirs:
            if heir.email:
                send_mail(
                    heir_subject,
                    heir_message.format(
                        user_address=heir.address,
                        link_tx=link.format(tx=message['transactionHash'])
                    ),
                    DEFAULT_FROM_EMAIL,
                    [heir.email]
                )
        self.contract.state = 'TRIGGERED'
        self.contract.save()
        if self.contract.user.email:
            send_mail(
                carry_out_subject,
                carry_out_message,
                DEFAULT_FROM_EMAIL,
                [self.contract.user.email]
            )

    def get_gaslimit(self):
        Cg = 1476117
        CBg = 28031
        return Cg + len(self.contract.heir_set.all()) * CBg + 3000 + 80000

    @blocking
    @postponable
    def deploy(self):
        return super().deploy()

@contract_details('Deferred payment contract')
class ContractDetailsDelayedPayment(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/DelayedPayment.sol'
    date = models.DateTimeField()
    user_address = models.CharField(max_length=50)
    recepient_address = models.CharField(max_length=50)
    recepient_email = models.CharField(max_length=200, null=True)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    def predeploy_validate(self):
        now = timezone.now()
        if self.date < now:
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
        return 25000000000000000

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        super().msg_deployed(message)

    def checked(self, message):
        pass

    def triggered(self, message):
        link = NETWORKS[self.eth_contract.contract.network.name]['link_tx']
        if self.recepient_email:
            send_mail(
                heir_subject,
                heir_message.format(
                    user_address=self.recepient_address,
                    link_tx=link.format(tx=message['transactionHash'])
                ),
                DEFAULT_FROM_EMAIL,
                [self.recepient_email]
            )
        self.contract.state = 'TRIGGERED'
        self.contract.save()
        if self.contract.user.email:
            send_mail(
                carry_out_subject,
                carry_out_message,
                DEFAULT_FROM_EMAIL,
                [self.contract.user.email]
            )
    
    def get_arguments(self, *args, **kwargs):
        return [
            self.user_address,
            self.recepient_address,
            2**256 - 1,
            int(self.date.timestamp()),
        ]

    def get_gaslimit(self):
        return 1700000

    @blocking
    @postponable
    def deploy(self):
        return super().deploy()


@contract_details('Pizza')
class ContractDetailsPizza(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/Pizza.sol'
    user_address = models.CharField(max_length=50)
    pizzeria_address = models.CharField(
        max_length=50, default='0x1eee4c7d88aadec2ab82dd191491d1a9edf21e9a'
    )
    timeout = models.IntegerField(default=60*60)
    code = models.IntegerField()
    salt = models.CharField(max_length=len(str(2**256)))
    pizza_cost = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0) # weis
    order_id = models.DecimalField(max_digits=50, decimal_places=0, unique=True)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None)

    @classmethod
    def min_cost(cls):
        return 0

@contract_details('MyWish ICO')
class ContractDetailsICO(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/ICO.sol'

    soft_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    hard_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    token_name = models.CharField(max_length=512)
    token_short_name = models.CharField(max_length=64)
    admin_address = models.CharField(max_length=50)
    is_transferable_at_once = models.BooleanField(default=False)
    start_date = models.IntegerField()
    stop_date = models.IntegerField()
    rate = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    decimals = models.IntegerField()
    platform_as_admin = models.BooleanField(default=False)
    temp_directory = models.CharField(max_length=36)
    time_bonuses = JSONField(null=True, default=None)
    amount_bonuses = JSONField(null=True, default=None)
    continue_minting = models.BooleanField(default=False)
    cold_wallet_address = models.CharField(max_length=50, default='')

    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='ico_details_token',
        on_delete=models.SET_NULL
    )
    eth_contract_crowdsale = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='ico_details_crowdsale',
        on_delete=models.SET_NULL
    )

    reused_token = models.BooleanField(default=False)
    token_type = models.CharField(max_length=32, default='ERC20')

    min_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )
    max_wei = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, default=None, null=True
    )


    def predeploy_validate(self):
        now = timezone.now()
        if self.start_date < now.timestamp():
            raise ValidationError({'result': 1}, code=400)
        token_holders = self.contract.tokenholder_set.all()
        for th in token_holders:
            if th.freeze_date:
                if th.freeze_date < now.timestamp() + 600:
                    raise ValidationError({'result': 2}, code=400)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='ETHEREUM_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        return int(2.49 * 10**18)

    def compile(self, eth_contract_attr_name='eth_contract_token'):
        print('ico_contract compile')
        test_logger.info('ico contract compile id=%d' %self.id)
        if self.temp_directory:
            print('already compiled')
            test_logger.error('already compiled')
            return
        dest, preproc_config = create_directory(self)
        token_holders = self.contract.tokenholder_set.all()
        amount_bonuses = add_amount_bonuses(self)
        time_bonuses = add_time_bonuses(self)
        preproc_params = {'constants': {}}
        preproc_params['constants'] = add_token_params(
            preproc_params['constants'], self, token_holders,
            not self.is_transferable_at_once,
            self.continue_minting
        )
        preproc_params['constants'] = add_crowdsale_params(
            preproc_params['constants'], self, time_bonuses, amount_bonuses
        )
        if self.min_wei:
            preproc_params["constants"]["D_MIN_VALUE_WEI"] = str(int(self.min_wei))
        if self.max_wei:
            preproc_params["constants"]["D_MAX_VALUE_WEI"] = str(int(self.max_wei))

        test_crowdsale_params(preproc_config, preproc_params, dest)
        address = NETWORKS[self.contract.network.name]['address']
        preproc_params = add_real_params(
            preproc_params, self.admin_address,
            address, self.cold_wallet_address
        )
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system(
                "/bin/bash -c 'cd {dest} && ./compile-crowdsale.sh'".format(dest=dest)
        ):
            raise Exception('compiler error while deploying')
        with open(path.join(dest, 'build/contracts/TemplateCrowdsale.json')) as f:
            crowdsale_json = json.loads(f.read())
        with open(path.join(dest, 'build/TemplateCrowdsale.sol')) as f:
            source_code = f.read()
        self.eth_contract_crowdsale = create_ethcontract_in_compile(
            crowdsale_json['abi'], crowdsale_json['bytecode'][2:],
            crowdsale_json['compiler']['version'], self.contract, source_code
        )
        if not self.reused_token:
            with open(path.join(dest, 'build/contracts/MainToken.json')) as f:
                token_json = json.loads(f.read())
            with open(path.join(dest, 'build/MainToken.sol')) as f:
                source_code = f.read()
            self.eth_contract_token = create_ethcontract_in_compile(
                token_json['abi'], token_json['bytecode'][2:],
                token_json['compiler']['version'], self.contract, source_code
            )
        self.save()
#        shutil.rmtree(dest)

    @blocking
    @postponable
    @check_transaction
    def msg_deployed(self, message):
        print('msg_deployed method of the ico contract')
        test_logger.info('msg_deployed method of the ico contract')
        address = NETWORKS[self.contract.network.name]['address']
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            take_off_blocking(self.contract.network.name)
            return
        if self.reused_token:
            self.contract.state = 'WAITING_ACTIVATION'
            self.contract.save()
            self.eth_contract_crowdsale.address = message['address']
            self.eth_contract_crowdsale.save()
            take_off_blocking(self.contract.network.name)
            print('status changed to waiting activation')
            test_logger.info('status changed to waiting activation')
            return
        if self.eth_contract_token.id == message['contractId']:
            self.eth_contract_token.address = message['address']
            self.eth_contract_token.save()
            self.deploy(eth_contract_attr_name='eth_contract_crowdsale')
        else:
            self.eth_contract_crowdsale.address = message['address']
            self.eth_contract_crowdsale.save()
            tr = abi.ContractTranslator(self.eth_contract_token.abi)
            par_int = ParInt(self.contract.network.name)
            nonce = int(par_int.eth_getTransactionCount(address, "pending"), 16) 
            print('nonce', nonce)
            print('transferOwnership message signed')
            test_logger.info('nonce %d' %nonce)
            test_logger.info('transferOwnership message signed')
            signed_data = sign_transaction(
                address, nonce, 100000, self.contract.network.name,
                dest=self.eth_contract_token.address,
                contract_data=binascii.hexlify(tr.encode_function_call(
                    'transferOwnership', [self.eth_contract_crowdsale.address]
                )).decode(),
            )
            self.eth_contract_token.tx_hash = par_int.eth_sendRawTransaction(
                '0x'+signed_data
            )
            self.eth_contract_token.save()
            test_logger.info('transferOwnership message sended')
            print('transferOwnership message sended')

    def get_gaslimit(self):
        return 3200000

    @blocking
    @postponable
    def deploy(self, eth_contract_attr_name='eth_contract_token'):
        if self.reused_token:
            eth_contract_attr_name = 'eth_contract_crowdsale'
        return super().deploy(eth_contract_attr_name)
        
    def get_arguments(self, eth_contract_attr_name):
        return {
                'eth_contract_token': [],
                'eth_contract_crowdsale': [self.eth_contract_token.address],
        }[eth_contract_attr_name]

    # token
    @blocking
    @postponable
#    @check_transaction
    def ownershipTransferred(self, message):
        address = NETWORKS[self.contract.network.name]['address']
        if message['contractId'] != self.eth_contract_token.id:
            if self.contract.state == 'WAITING_FOR_DEPLOYMENT':
                take_off_blocking(self.contract.network.name)
            print('ignored', flush=True)
            test_logger.error('ignored id %d' %self.id)
            return
        if self.contract.state in ('ACTIVE', 'ENDED'):
            take_off_blocking(self.contract.network.name)
            return
        if self.contract.state == 'WAITING_ACTIVATION':
            self.contract.state = 'WAITING_FOR_DEPLOYMENT'
            self.contract.save()
            # continue deploy: call init
        tr = abi.ContractTranslator(self.eth_contract_crowdsale.abi)
        par_int = ParInt(self.contract.network.name)
        nonce = int(par_int.eth_getTransactionCount(address, "pending"), 16)
        print('nonce', nonce)
        test_logger.info('nonce %d' %nonce)
        print('init message signed')
        test_logger.info('init message signed')
        signed_data = sign_transaction(
            address, nonce,
            100000 + 80000 * self.contract.tokenholder_set.all().count(),
            self.contract.network.name,
            dest=self.eth_contract_crowdsale.address,
            contract_data=binascii.hexlify(
                tr.encode_function_call('init', [])
            ).decode()
        )
        self.eth_contract_crowdsale.tx_hash = par_int.eth_sendRawTransaction(
            '0x'+signed_data
        )
        self.eth_contract_crowdsale.save()
        print('init message sended')
        test_logger.info('init message sended')


    # crowdsale
    @postponable
    @check_transaction
    def initialized(self, message):
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            return
        take_off_blocking(self.contract.network.name)
        if message['contractId'] != self.eth_contract_crowdsale.id:
            print('ignored', flush=True)
            test_logger.error('ignored id' %self.id)
            return
        self.contract.state = 'ACTIVE'
        self.contract.save()
        if self.eth_contract_token.original_contract.contract_type == 5:
            self.eth_contract_token.original_contract.state = 'UNDER_CROWDSALE'
            self.eth_contract_token.original_contract.save()
        network_link = NETWORKS[self.contract.network.name]['link_address']
        network_name = MAIL_NETWORK[self.contract.network.name]
        if self.contract.user.email:
            send_mail(
                    ico_subject,
                    ico_text.format(
                            link1=network_link.format(
                                address=self.eth_contract_token.address,
                            ),
                            link2=network_link.format(
                                address=self.eth_contract_crowdsale.address
                            ),
                            network_name=network_name
                    ),
                    DEFAULT_FROM_EMAIL,
                    [self.contract.user.email]
            )

    def finalized(self, message):
        if not self.continue_minting and self.eth_contract_token.original_contract.state != 'ENDED':
            self.eth_contract_token.original_contract.state = 'ENDED'
            self.eth_contract_token.original_contract.save()
        if self.eth_contract_crowdsale.contract.state != 'ENDED':
            self.eth_contract_crowdsale.contract.state = 'ENDED'
            self.eth_contract_crowdsale.contract.save()

    def check_contract(self):
        pass
        

@contract_details('Token contract')
class ContractDetailsToken(CommonDetails):
    token_name = models.CharField(max_length=512)
    token_short_name = models.CharField(max_length=64)
    admin_address = models.CharField(max_length=50)
    decimals = models.IntegerField()
    token_type = models.CharField(max_length=32, default='ERC20')
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='token_details_token',
        on_delete=models.SET_NULL
    )
    future_minting = models.BooleanField(default=False)
    temp_directory = models.CharField(max_length=36)

    def predeploy_validate(self):
        now = timezone.now()
        token_holders = self.contract.tokenholder_set.all()
        for th in token_holders:
            if th.freeze_date:
                if th.freeze_date < now.timestamp() + 600:
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
        return int(0.99 * 10**18)

    def get_arguments(self, eth_contract_attr_name):
        return []

    def compile(self, eth_contract_attr_name='eth_contract_token'):
        print('standalone token contract compile')
        test_logger.info('standalone token contract compile')
        if self.temp_directory:
            print('already compiled')
            test_logger.error('already compiled id=%d' %self.id)
            return
        dest, preproc_config = create_directory(self)
        token_holders = self.contract.tokenholder_set.all()
        preproc_params = {"constants": {"D_ONLY_TOKEN": True}}
        preproc_params['constants'] = add_token_params(
            preproc_params['constants'], self, token_holders,
            False, self.future_minting
        )
        test_token_params(preproc_config, preproc_params, dest)
        preproc_params['constants']['D_CONTRACTS_OWNER'] = self.admin_address
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && ./compile-token.sh'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        with open(path.join(dest, 'build/contracts/MainToken.json')) as f:
            token_json = json.loads(f.read())
        with open(path.join(dest, 'build/MainToken.sol')) as f:
            source_code = f.read()
        self.eth_contract_token = create_ethcontract_in_compile(
            token_json['abi'], token_json['bytecode'][2:],
            token_json['compiler']['version'], self.contract, source_code
        )
        self.save()

    @blocking
    @postponable
    def deploy(self, eth_contract_attr_name='eth_contract_token'):
        return super().deploy(eth_contract_attr_name)

    def get_gaslimit(self):
        return 3200000

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        res = super().msg_deployed(message, 'eth_contract_token')
        if not self.future_minting:
            self.contract.state = 'ENDED'
            self.contract.save()
        return res

    def ownershipTransferred(self, message):
        if self.eth_contract_token.original_contract.state not in (
                'UNDER_CROWDSALE', 'ENDED'
        ):
            self.eth_contract_token.original_contract.state = 'UNDER_CROWDSALE'
            self.eth_contract_token.original_contract.save()

    def finalized(self, message):
        if self.eth_contract_token.original_contract.state != 'ENDED':
            self.eth_contract_token.original_contract.state = 'ENDED'
            self.eth_contract_token.original_contract.save()
        if (self.eth_contract_token.original_contract.id !=
                self.eth_contract_token.contract.id and
                    self.eth_contract_token.contract.state != 'ENDED'):
            self.eth_contract_token.contract.state = 'ENDED'
            self.eth_contract_token.contract.save()

    def check_contract(self):
        pass


class Heir(models.Model):
    contract = models.ForeignKey(Contract)
    address = models.CharField(max_length=50)
    percentage = models.IntegerField()
    email = models.CharField(max_length=200, null=True)


class TokenHolder(models.Model):
    contract = models.ForeignKey(Contract)
    name = models.CharField(max_length=512, null=True)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    freeze_date = models.IntegerField(null=True)


class NeoContract(EthContract):
    pass


@contract_details('NEO contract')
class ContractDetailsNeo(CommonDetails):

    temp_directory = models.CharField(max_length=36, default='')
    parameter_list = JSONField(default={})
    neo_contract = models.ForeignKey(NeoContract, null=True, default=None)
    storage_area = models.BooleanField(default=False)
    token_name = models.CharField(max_length=50)
    token_short_name = models.CharField(max_length=10)
    decimals = models.IntegerField()
    admin_address = models.CharField(max_length=70)
    future_minting = models.BooleanField(default=False)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='NEO_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(details, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        if details.get('storage_area', False):
            return 600
        return 200

    def predeploy_validate(self):
        pass

    def compile(self):
        print('standalone token contract compile')
        test_logger.info('standalone token contract compile')
        if self.temp_directory:
            print('already compiled')
            test_logger.error('already compiled id %d' %self.id)
            return
        dest, preproc_config = create_directory(
            self, 'lastwill/neo-ico-contracts/*', 'token-config.json'
        )
        token_holders = self.contract.tokenholder_set.all()
        preproc_params = {"constants": {
            "D_NAME": self.token_name,
            "D_SYMBOL": self.token_short_name,
            "D_DECIMALS": self.decimals,
            "D_PREMINT_COUNT": len(token_holders),
            "D_OWNER": self.admin_address,
            "D_CONTINUE_MINTING": self.future_minting
        }}
        for ind, th in enumerate(token_holders):
            preproc_params["constants"]["D_PREMINT_ADDRESS_" + str(ind)] = str(th.address)
            preproc_params["constants"]["D_PREMINT_AMOUNT_" + str(ind)] = [
                int(x) for x in int(th.amount).to_bytes(
                    math.floor(math.log(int(th.amount) or 1, 256)) + 1, 'little'
                )
            ]
            preproc_params["constants"]["D_PREMINT_AMOUNT_" + str(ind)].append(0)
            preproc_params["constants"]["D_PREMINT_FREEZE_" + str(ind)] = str(th.freeze_date) if th.freeze_date else 0

        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system("/bin/bash -c 'cd {dest} && ./2_compile_token.sh'".format(dest=dest)):
            raise Exception('compiler error while deploying')
        print('dest', dest, flush=True)
        test_logger.info('dest %s' %dest)
        test_neo_token_params(preproc_config, preproc_params, dest)
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))

        with open(path.join(
                dest,
                'NEP5.Contract/bin/Release/netcoreapp2.0/publish/NEP5.Contract.abi.json'
        )) as f:
            token_json = json.loads(f.read())
        with open(path.join(
                dest,
                'NEP5.Contract/bin/Release/netcoreapp2.0/publish/NEP5.Contract.avm'
        ), mode='rb') as f:
            bytecode = f.read()
        with open(path.join(dest, 'NEP5.Contract/Nep5Token.cs')) as f:
            source_code = f.read()
        neo_contract = NeoContract()
        neo_contract.abi = token_json
        neo_contract.bytecode = binascii.hexlify(bytecode).decode()
        neo_contract.source_code = source_code
        neo_contract.contract = self.contract
        neo_contract.original_contract = self.contract
        neo_contract.save()
        self.neo_contract_crowdsale = neo_contract
        self.save()

    @blocking
    @postponable
    def deploy(self, contract_params='0710', return_type='05'):
        self.compile()
        from_addr = NETWORKS[self.contract.network.name]['address']
        bytecode = self.neo_contract_crowdsale.bytecode
        neo_int = NeoInt(self.contract.network.name)
        print('from address', from_addr)
        test_logger.info('from address %s' %from_addr)
        details = {
            'name': 'WISH',
            'description': 'NEO smart contract',
            'email': 'support@mywish.io',
            'version': '1',
            'author': 'MyWish'
        }
        param_list = {
                'from_addr': from_addr,
                'bin': bytecode,
                'needs_storage': True,
                'needs_dynamic_invoke': False,
                'contract_params': contract_params,
                'return_type': return_type,
                'details': details,
        }
        response = neo_int.mw_construct_deploy_tx(param_list)
        print('construct response', response, flush=True)
        binary_tx = response['tx']
        contract_hash = response['hash']

        tx = ContractTransaction.DeserializeFromBufer(
            binascii.unhexlify(binary_tx)
        )
        tx = sign_neo_transaction(tx, binary_tx, from_addr)
        print('after sign', tx.ToJson()['txid'], flush=True)
        test_logger.info('after sign %s' %tx.ToJson()['txid'])
        ms = StreamManager.GetStream()
        writer = BinaryWriter(ms)
        tx.Serialize(writer)
        ms.flush()
        signed_tx = ms.ToArray()
        print('full tx:', flush=True)
        print(signed_tx, flush=True)
        
        result = neo_int.sendrawtransaction(signed_tx.decode())
        print(result, flush=True)
        if not result:
            raise TxFail()
        print('contract hash:', contract_hash)
        test_logger.info('contract hash: %s' %contract_hash)
        print('result of send raw transaction: ', result)
        test_logger.info('result of send raw transaction: %s' %result)

        self.neo_contract.address = contract_hash
        self.neo_contract.tx_hash = tx.ToJson()['txid']
        self.neo_contract.save()

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        neo_int = NeoInt(self.contract.network.name)
        from_addr = NETWORKS[self.contract.network.name]['address']
        param_list = {
            'from_addr': from_addr,
            'contract_params': [
                {'type': str(ContractParameterType.String), 'value': 'init'},
                {'type': str(ContractParameterType.Array), 'value': []}
            ],
            'addr': self.neo_contract.address,
        }

        response = neo_int.mw_construct_invoke_tx(param_list)

        binary_tx = response['tx']

        tx = ContractTransaction.DeserializeFromBufer(
            binascii.unhexlify(binary_tx)
        )
        tx = sign_neo_transaction(tx, binary_tx, from_addr)
        print('after sign', tx.ToJson()['txid'])
        ms = StreamManager.GetStream()
        writer = BinaryWriter(ms)
        tx.Serialize(writer)
        ms.flush()
        signed_tx = ms.ToArray()
        print('signed_tx', signed_tx)
        result = neo_int.sendrawtransaction(signed_tx.decode())
        print(result, flush=True)
        if not result:
            raise TxFail()
        print('result of send raw transaction: ', result)

        assert(result)
        self.contract.save()
        return

    @postponable
    @check_transaction
    def initialized(self, message):
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            return

        take_off_blocking(self.contract.network.name)

        self.contract.state = 'ACTIVE' if self.future_minting else 'ENDED'
        self.contract.save()

        if self.contract.user.email:
            send_mail(
                    common_subject,
                    neo_token_text.format(
                        addr = Crypto.ToAddress(UInt160.ParseString(self.neo_contract.address)),
                    ),
                    DEFAULT_FROM_EMAIL,
                    [self.contract.user.email]
            )

    def finalized(self, message):
        self.contract.state = 'ENDED'
        self.contract.save()


@contract_details('MyWish ICO')
class ContractDetailsNeoICO(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/ICO.sol'

    hard_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    token_name = models.CharField(max_length=512)
    token_short_name = models.CharField(max_length=64)
    admin_address = models.CharField(max_length=50)
    start_date = models.IntegerField()
    stop_date = models.IntegerField()
    rate = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    decimals = models.IntegerField()
    temp_directory = models.CharField(max_length=36)

    neo_contract_crowdsale = models.ForeignKey(
        NeoContract,
        null=True,
        default=None,
        related_name='neo_ico_details_crowdsale',
        on_delete=models.SET_NULL
    )

    reused_token = models.BooleanField(default=False)

    def compile(self):
        print('standalone token contract compile')
        test_logger.info('standalone token contract compile')
        if self.temp_directory:
            print('already compiled')
            test_logger.error('already compiled id %d' %self.id)
            return
        dest, preproc_config = create_directory(
            self, 'lastwill/neo-ico-contracts/*', 'crowdsale-config.json'
        )
        token_holders = self.contract.tokenholder_set.all()
        preproc_params = {"constants": {
            "D_NAME": self.token_name,
            "D_SYMBOL": self.token_short_name,
            "D_DECIMALS": int(self.decimals),
            "D_PREMINT_COUNT": len(token_holders),
            "D_OWNER": self.admin_address,
            "D_START_TIME": self.start_date,
            "D_END_TIME": self.stop_date,
            "D_RATE": int(self.rate),
            "D_HARD_CAP_NEO": str(self.hard_cap)
        }}
        for ind, th in enumerate(token_holders):
            preproc_params["constants"]["D_PREMINT_ADDRESS_" + str(ind)] = str(th.address)
            preproc_params["constants"]["D_PREMINT_AMOUNT_" + str(ind)] = [
                int(x) for x in int(th.amount).to_bytes(
                    math.floor(math.log(int(th.amount) or 1, 256)) + 1, 'little'
                )
            ]
            preproc_params["constants"]["D_PREMINT_AMOUNT_" + str(ind)].append(0)
            print('premint amount is', preproc_params["constants"]["D_PREMINT_AMOUNT_" + str(ind)], flush=True)
            preproc_params["constants"]["D_PREMINT_FREEZE_" + str(ind)] = str(th.freeze_date) if th.freeze_date else 0

        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system("/bin/bash -c 'cd {dest} && ./2_compile_crowdsale.sh'".format(dest=dest)):
            raise Exception('compiler error while deploying')
        print('dest', dest, flush=True)
        test_logger.info('dest %s' %dest)
        test_neo_ico_params(preproc_config, preproc_params, dest)
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))

        with open(path.join(
                dest,
                'Crowdsale.Contract/bin/Release/netcoreapp2.0/publish/Crowdsale.Contract.abi.json'
        )) as f:
            token_json = json.loads(f.read())
        with open(path.join(
                dest,
                'Crowdsale.Contract/bin/Release/netcoreapp2.0/publish/Crowdsale.Contract.avm'
        ), mode='rb') as f:
            bytecode = f.read()
        with open(path.join(dest, 'Crowdsale.Contract/Crowdsale.cs')) as f:
            source_code = f.read()
        neo_contract_crowdsale = NeoContract()
        neo_contract_crowdsale.abi = token_json
        neo_contract_crowdsale.bytecode = binascii.hexlify(bytecode).decode()
        neo_contract_crowdsale.source_code = source_code
        neo_contract_crowdsale.contract = self.contract
        neo_contract_crowdsale.original_contract = self.contract
        neo_contract_crowdsale.save()
        self.neo_contract_crowdsale = neo_contract_crowdsale
        self.save()

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='NEO_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(details, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        if details.get('storage_area', False):
            return 600
        return 200

    def predeploy_validate(self):
        pass

    def deploy(self, contract_params='0710', return_type='05'):
        self.compile()
        from_addr = NETWORKS[self.contract.network.name]['address']
        bytecode = self.neo_contract_crowdsale.bytecode
        neo_int = NeoInt(self.contract.network.name)
        print('from address', from_addr)
        test_logger.info('from address %s' % from_addr)
        details = {
            'name': 'WISH',
            'description': 'NEO smart contract',
            'email': 'support@mywish.io',
            'version': '1',
            'author': 'MyWish'
        }
        param_list = {
            'from_addr': from_addr,
            'bin': bytecode,
            'needs_storage': True,
            'needs_dynamic_invoke': False,
            'contract_params': contract_params,
            'return_type': return_type,
            'details': details,
        }
        response = neo_int.mw_construct_deploy_tx(param_list)
        print('construct response', response, flush=True)
        binary_tx = response['tx']
        contract_hash = response['hash']

        tx = ContractTransaction.DeserializeFromBufer(
            binascii.unhexlify(binary_tx)
        )
        tx = sign_neo_transaction(tx, binary_tx, from_addr)
        print('after sign', tx.ToJson()['txid'], flush=True)
        test_logger.info('after sign %s' % tx.ToJson()['txid'])
        ms = StreamManager.GetStream()
        writer = BinaryWriter(ms)
        tx.Serialize(writer)
        ms.flush()
        signed_tx = ms.ToArray()
        print('full tx:', flush=True)
        print(signed_tx, flush=True)

        result = neo_int.sendrawtransaction(signed_tx.decode())
        print(result, flush=True)
        if not result:
            raise TxFail()
        print('contract hash:', contract_hash)
        test_logger.info('contract hash: %s' % contract_hash)
        print('result of send raw transaction: ', result)
        test_logger.info('result of send raw transaction: %s' % result)

        self.neo_contract_crowdsale.address = contract_hash
        self.neo_contract_crowdsale.tx_hash = tx.ToJson()['txid']
        self.neo_contract_crowdsale.save()

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        neo_int = NeoInt(self.contract.network.name)
        from_addr = NETWORKS[self.contract.network.name]['address']
        param_list = {
            'from_addr': from_addr,
            'contract_params': [
                {'type': str(ContractParameterType.String), 'value': 'init'},
                {'type': str(ContractParameterType.Array), 'value': []}
            ],
            'addr': self.neo_contract_crowdsale.address,
        }

        response = neo_int.mw_construct_invoke_tx(param_list)

        binary_tx = response['tx']

        tx = ContractTransaction.DeserializeFromBufer(
            binascii.unhexlify(binary_tx)
        )
        tx = sign_neo_transaction(tx, binary_tx, from_addr)
        print('after sign', tx.ToJson()['txid'])
        ms = StreamManager.GetStream()
        writer = BinaryWriter(ms)
        tx.Serialize(writer)
        ms.flush()
        signed_tx = ms.ToArray()
        print('signed_tx', signed_tx)
        result = neo_int.sendrawtransaction(signed_tx.decode())
        print(result, flush=True)
        if not result:
            raise TxFail()
        print('result of send raw transaction: ', result)

        assert(result)
        self.contract.save()
        return

    @postponable
    @check_transaction
    def initialized(self, message):
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            return

        take_off_blocking(self.contract.network.name)

        self.contract.state = 'ENDED'
        self.contract.save()

        if self.contract.user.email:
            send_mail(
                    common_subject,
                    neo_token_text.format(
                        addr = Crypto.ToAddress(UInt160.ParseString(self.neo_contract_crowdsale.address)),
                    ),
                    DEFAULT_FROM_EMAIL,
                    [self.contract.user.email]
            )

    def finalized(self, message):
        self.contract.state = 'ENDED'
        self.contract.save()
