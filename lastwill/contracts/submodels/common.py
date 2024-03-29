import binascii
import os
import uuid
import binascii
import pika
import contextlib
from copy import deepcopy
from os import path

import pika
from base58 import b58decode
from django.apps import apps
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from ethereum import abi
from hdwallet import BIP44HDWallet
from hdwallet.symbols import ETH
from neo.Core.Witness import Witness
from neo.Settings import settings
from neocore.Cryptography.Crypto import Crypto
from neocore.UInt160 import UInt160
from requests_http_signature import HTTPSignatureAuth

from email_messages import *
from lastwill.consts import (AVAILABLE_CONTRACT_TYPES, CONTRACT_GAS_LIMIT, ETH_COMMON_GAS_PRICES, MAIL_NETWORK,
                             MAX_WEI_DIGITS, NET_DECIMALS, NETWORK_TYPES)
from lastwill.contracts.decorators import *
from lastwill.deploy.models import Network
from lastwill.parint import *
from lastwill.promo.utils import create_promocode
from lastwill.settings import (CONTRACTS_DIR, CONTRACTS_TEMP_DIR, GAS_API_URL, KEY_ID, NETWORKS, ROOT_EXT_KEY,
                               SECRET_KEY, SIGNER, SPEEDLVL, WEB3_ATTEMPT_COOLDOWN)
from lastwill.telegram_bot.tasks import send_message_to_subs
from mailings_tasks import send_promo_mainnet, send_testnet_gift_emails


def address_to_scripthash(address):
    data = b58decode(address)
    if len(data) != 25:
        raise ValueError('Not correct Address, wrong length.')
    if data[0] != settings.ADDRESS_VERSION:
        raise ValueError('Not correct Coin Version')
    checksum = Crypto.Default().Hash256(data[:21])[:4]
    if checksum != data[21:]:
        raise Exception('Address format error')
    return UInt160(data=data[1:21]).ToBytes()


def add_token_params(params, details, token_holders, pause, cont_mint):
    params["D_ERC"] = details.token_type
    params["D_NAME"] = details.token_name
    params["D_SYMBOL"] = details.token_short_name
    params["D_DECIMALS"] = details.decimals
    params["D_CONTINUE_MINTING"] = cont_mint
    params["D_CONTRACTS_OWNER"] = "0x8ffff2c69f000c790809f6b8f9abfcbaab46b322"
    params["D_PAUSE_TOKENS"] = pause
    params["D_PREMINT_COUNT"] = len(token_holders)
    params["D_PREMINT_ADDRESSES"] = ','.join(map(lambda th: 'address(%s)' % th.address, token_holders))
    params["D_PREMINT_AMOUNTS"] = ','.join(map(lambda th: 'uint(%s)' % th.amount, token_holders))
    params["D_PREMINT_FREEZES"] = ','.join(
        map(lambda th: 'uint64(%s)' % (th.freeze_date if th.freeze_date else 0), token_holders))
    return params


def add_crowdsale_params(params, details, time_bonuses, amount_bonuses):
    params["D_CAN_CHANGE_START_TIME"] = "true" if details.allow_change_dates and not time_bonuses else "false"
    params["D_CAN_CHANGE_END_TIME"] = "true" if details.allow_change_dates else "false"
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
    params["D_WEI_RAISED_STARTS_BOUNDARIES"] = ','.join(map(lambda b: 'uint(%s)' % b['min_amount'], time_bonuses))
    params["D_WEI_RAISED_ENDS_BOUNDARIES"] = ','.join(map(lambda b: 'uint(%s)' % b['max_amount'], time_bonuses))
    params["D_TIME_STARTS_BOUNDARIES"] = ','.join(map(lambda b: 'uint64(%s)' % b['min_time'], time_bonuses))
    params["D_TIME_ENDS_BOUNDARIES"] = ','.join(map(lambda b: 'uint64(%s)' % b['max_time'], time_bonuses))
    params["D_WEI_RAISED_AND_TIME_MILLIRATES"] = ','.join(
        map(lambda b: 'uint(%s)' % (int(10 * b['bonus'])), time_bonuses))
    params["D_WEI_AMOUNT_BONUS_COUNT"] = len(amount_bonuses)
    params["D_WEI_AMOUNT_BOUNDARIES"] = ','.join(map(lambda b: 'uint(%s)' % b['max_amount'], reversed(amount_bonuses)))
    params["D_WEI_AMOUNT_MILLIRATES"] = ','.join(
        map(lambda b: 'uint(%s)' % (int(10 * b['bonus'])), reversed(amount_bonuses)))
    params["D_MYWISH_ADDRESS"] = '0xe33c67fcb6f17ecadbc6fa7e9505fc79e9c8a8fd'
    params["D_WHITELIST_ENABLED"] = details.whitelist
    return params


def add_amount_bonuses(details):
    amount_bonuses = []
    if details.amount_bonuses:
        curr_min_amount = 0
        for bonus in details.amount_bonuses:
            amount_bonuses.append({'max_amount': bonus['min_amount'], 'bonus': bonus['bonus']})
            if int(bonus['min_amount']) > curr_min_amount:  # fill gap with zero
                amount_bonuses.append({'max_amount': bonus['max_amount'], 'bonus': 0})
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
    print(details.temp_directory, flush=True)
    sour = path.join(CONTRACTS_DIR, sour_path)
    dest = path.join(CONTRACTS_TEMP_DIR, details.temp_directory)
    os.makedirs(dest)
    os.system('cp -as {sour} {dest}'.format(sour=sour, dest=dest))

    if config_name:
        preproc_config = os.path.join(dest, config_name)
        with contextlib.suppress(FileNotFoundError):
            os.unlink(preproc_config)
    else:
        preproc_config = ''
    return dest, preproc_config


def test_investment_pool_params(config, params, dest):
    with open(config, 'w') as f:
        f.write(json.dumps(params))
    if os.system("/bin/bash -c 'cd {dest} && yarn compile'".format(dest=dest)):
        raise Exception('compiler error while testing')
    if os.system("/bin/bash -c 'cd {dest} &&  yarn test'".format(dest=dest)):
        raise Exception('testing error')


def test_crowdsale_params(config, params, dest):
    with open(config, 'w') as f:
        f.write(json.dumps(params))
    if os.system("/bin/bash -c 'cd {dest} && yarn compile-crowdsale'".format(dest=dest)):
        raise Exception('compiler error while testing')
    if os.system("/bin/bash -c 'cd {dest} &&  yarn test-crowdsale'".format(dest=dest)):
        raise Exception('testing error')


def test_token_params(config, params, dest):
    with open(config, 'w') as f:
        f.write(json.dumps(params))
    if os.system("/bin/bash -c 'cd {dest} && yarn compile-token'".format(dest=dest)):
        raise Exception('compiler error while deploying')
    if os.system("/bin/bash -c 'cd {dest} && yarn test-token'".format(dest=dest)):
        raise Exception('compiler error while testing')


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


def send_in_queue(contract_id, type, queue):
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        os.environ.get('RABBITMQ_HOST', 'localhost'),
        os.environ.get('RABBITMQ_PORT', 5672),
        'mywill',
        pika.PlainCredentials('java', 'java'),
    ))
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True, auto_delete=False, exclusive=False)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps({
            'status': 'COMMITTED',
            'contractId': contract_id
        }),
        properties=pika.BasicProperties(type=type),
    )
    connection.close()


def sign_transaction(address,
                     nonce,
                     gaslimit,
                     value=None,
                     dest=None,
                     contract_data=None,
                     gas_price=None,
                     chain_id=None,
                     child_id=None):
    data = {
        'from': address,
        'nonce': nonce,
        'gas': gaslimit,
    }
    if value:
        data['value'] = value
    if dest:
        data['to'] = dest
    if contract_data:
        data['data'] = contract_data
    if gas_price:
        data['gasPrice'] = gas_price

    if chain_id:
        data['chainId'] = chain_id
    if child_id:
        data['child_id'] = child_id

    auth = HTTPSignatureAuth(key=SECRET_KEY, key_id=KEY_ID)
    signed_response = requests.post(SIGNER, auth=auth, json=data)
    signed_data = json.loads(signed_response.content.decode())
    return signed_data['signed_tx']


def sign_neo_transaction(tx, binary_tx, address):
    scripts = requests.post('http://{}/neo_sign/'.format(SIGNER), json={
        'binary_tx': binary_tx,
        'address': address
    }).json()
    tx.scripts = [Witness(
        x['invocation'].encode(),
        x['verification'].encode(),
    ) for x in scripts]
    return tx


def get_whitelabel_address(contract_id):
    hd_wallet = BIP44HDWallet(symbol=ETH, account=0, change=False, address=0)
    hd_wallet.from_root_xprivate_key(ROOT_EXT_KEY)
    derived_wallet = hd_wallet.from_index(contract_id)
    address = derived_wallet.address()
    return address


def transfer_crypto(details, dest):
    eth_int = EthereumProvider().get_provider(network=details.contract.network.name)
    address = NETWORKS[details.contract.network.name]['address']
    nonce = int(eth_int.eth_getTransactionCount(address, "latest"), 16)
    gas_price_current = details.get_gasstation_gasprice() or int(1.1 * int(eth_int.eth_gasPrice(), 16))
    gas_price_fixed = ETH_COMMON_GAS_PRICES[details.contract.network.name] * NET_DECIMALS['ETH_GAS_PRICE']
    gas_price = gas_price_current if gas_price_current < gas_price_fixed else gas_price_fixed
    gas_limit = CONTRACT_GAS_LIMIT['WHITELABEL']
    eth_amount = hex(int(1.2 * (gas_price * CONTRACT_GAS_LIMIT['TOKEN'])))
    chain_id = int(eth_int.eth_chainId(), 16)

    signed_data = sign_transaction(address,
                                   nonce,
                                   gas_limit,
                                   value=eth_amount,
                                   dest=dest,
                                   gas_price=gas_price,
                                   chain_id=chain_id)

    tx_hash = eth_int.eth_sendRawTransaction(signed_data)
    return tx_hash


'''
contract as user see it at site. contract as service. can contain more then one real ethereum contracts
'''


class Contract(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    network = models.ForeignKey(Network, default=1, on_delete=models.CASCADE)

    address = models.CharField(max_length=50, null=True, default=None)
    owner_address = models.CharField(max_length=50, null=True, default=None)
    user_address = models.CharField(max_length=50, null=True, default=None)

    balance = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True, default=None)
    cost = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)

    name = models.CharField(max_length=200, null=True, default=None)
    state = models.CharField(max_length=63, default='CREATED')
    contract_type = models.IntegerField(default=0)

    source_code = models.TextField()
    bytecode = models.TextField()
    abi = JSONField(default={})
    compiler_version = models.CharField(max_length=200, null=True, default=None)

    created_date = models.DateTimeField(auto_now_add=True)
    deployed_at = models.DateTimeField(null=True, default=None)
    postponed_at = models.DateTimeField(null=True, default=None)
    deploy_started_at = models.DateTimeField(null=True, default=None)

    check_interval = models.IntegerField(null=True, default=None)
    active_to = models.DateTimeField(null=True, default=None)
    last_check = models.DateTimeField(null=True, default=None)
    next_check = models.DateTimeField(null=True, default=None)

    invisible = models.BooleanField(default=False)

    def __str__(self):
        return f"ID {self.id} {self.name} for {self.user.__str__()} in {self.network.name}"

    def save(self, *args, **kwargs):
        # disable balance saving to prevent collisions with java daemon
        print(args)
        str_args = ','.join([str(x) for x in args])
        if self.id:
            kwargs['update_fields'] = list({f.name for f in Contract._meta.fields if f.name not in ('balance', 'id')} &
                                           set(kwargs.get('update_fields', [f.name for f in Contract._meta.fields])))
        return super().save(*args, **kwargs)

    def get_details(self):
        return getattr(self, self.get_details_model(self.contract_type).__name__.lower() + '_set').first()

    @classmethod
    def get_all_details_model(cls):
        contract_details_types = {}

        lastwill = apps.get_model('contracts', 'ContractDetailsLastwill')
        lostkey = apps.get_model('contracts', 'ContractDetailsLostKey')
        deffered = apps.get_model('contracts', 'ContractDetailsDelayedPayment')
        ico = apps.get_model('contracts', 'ContractDetailsICO')
        token = apps.get_model('contracts', 'ContractDetailsToken')
        neo = apps.get_model('contracts', 'ContractDetailsNeo')
        neo_ico = apps.get_model('contracts', 'ContractDetailsNeoICO')
        airdrop = apps.get_model('contracts', 'ContractDetailsAirdrop')
        investment = apps.get_model('contracts', 'ContractDetailsInvestmentPool')
        eos_token = apps.get_model('contracts', 'ContractDetailsEOSToken')
        eos_account = apps.get_model('contracts', 'ContractDetailsEOSAccount')
        eos_ico = apps.get_model('contracts', 'ContractDetailsEOSICO')
        eos_airdrop = apps.get_model('contracts', 'ContractDetailsEOSAirdrop')
        eos_token_standalone = apps.get_model('contracts', 'ContractDetailsEOSTokenSA')
        tron_token = apps.get_model('contracts', 'ContractDetailsTRONToken')
        game_asset = apps.get_model('contracts', 'ContractDetailsGameAssets')
        tron_airdrop = apps.get_model('contracts', 'ContractDetailsTRONAirdrop')
        tron_lostkey = apps.get_model('contracts', 'ContractDetailsTRONLostkey')
        eth_lostkey_tokens = apps.get_model('contracts', 'ContractDetailsLostKeyTokens')
        swap = apps.get_model('contracts', 'ContractDetailsSWAPS')
        waves = apps.get_model('contracts', 'ContractDetailsWavesSTO')
        swap2 = apps.get_model('contracts', 'ContractDetailsSWAPS2')
        token_protector = apps.get_model('contracts', 'ContractDetailsTokenProtector')
        binance_lastwill = apps.get_model('contracts', 'ContractDetailsBinanceLastwill')
        binance_lostkey = apps.get_model('contracts', 'ContractDetailsBinanceLostKey')
        binance_deffered = apps.get_model('contracts', 'ContractDetailsBinanceDelayedPayment')
        binance_ico = apps.get_model('contracts', 'ContractDetailsBinanceICO')
        binance_token = apps.get_model('contracts', 'ContractDetailsBinanceToken')
        binance_airdrop = apps.get_model('contracts', 'ContractDetailsBinanceAirdrop')
        binance_investment = apps.get_model('contracts', 'ContractDetailsBinanceInvestmentPool')
        binance_lostkey_tokens = apps.get_model('contracts', 'ContractDetailsBinanceLostKeyTokens')
        matic_ico = apps.get_model('contracts', 'ContractDetailsMaticICO')
        matic_token = apps.get_model('contracts', 'ContractDetailsMaticToken')
        matic_airdrop = apps.get_model('contracts', 'ContractDetailsMaticAirdrop')
        xinfin_token = apps.get_model('contracts', 'ContractDetailsXinFinToken')
        hecochain_token = apps.get_model('contracts', 'ContractDetailsHecoChainToken')
        hecochain_ico = apps.get_model('contracts', 'ContractDetailsHecoChainICO')
        moonriver_token = apps.get_model('contracts', 'ContractDetailsMoonriverToken')
        solana_token = apps.get_model('contracts', 'ContractDetailsSolanaToken')
        near_token = apps.get_model('contracts', 'ContractDetailsNearToken')

        contract_details_types[0] = {'name': 'Will contract', 'model': lastwill}
        contract_details_types[1] = {'name': 'Wallet contract (lost key)', 'model': lostkey}
        contract_details_types[2] = {'name': 'Deferred payment contract', 'model': deffered}
        contract_details_types[4] = {'name': 'MyWish ICO', 'model': ico}
        contract_details_types[5] = {'name': 'Token contract', 'model': token}
        contract_details_types[6] = {'name': 'NEO contract', 'model': neo}
        contract_details_types[7] = {'name': 'MyWish NEO ICO', 'model': neo_ico}
        contract_details_types[8] = {'name': 'Airdrop', 'model': airdrop}
        contract_details_types[9] = {'name': 'InvestmentPool', 'model': investment}
        contract_details_types[10] = {'name': 'EOS Token', 'model': eos_token}
        contract_details_types[11] = {'name': 'EOS Account', 'model': eos_account}
        contract_details_types[12] = {'name': 'EOS ICO', 'model': eos_ico}
        contract_details_types[13] = {'name': 'EOS Airdrop', 'model': eos_airdrop}
        contract_details_types[14] = {'name': 'EOS Token standalone', 'model': eos_token_standalone}
        contract_details_types[15] = {'name': 'TRON Token', 'model': tron_token}
        contract_details_types[16] = {'name': 'Game Assets', 'model': game_asset}
        contract_details_types[17] = {'name': 'TRON Airdrop', 'model': tron_airdrop}
        contract_details_types[18] = {'name': 'TRON LostKey', 'model': tron_lostkey}
        contract_details_types[19] = {'name': 'ETH LostKey with tokens', 'model': eth_lostkey_tokens}
        contract_details_types[20] = {'name': 'SWAPS Contract', 'model': swap}
        contract_details_types[22] = {'name': 'WAVES Contract STO', 'model': waves}
        contract_details_types[21] = {'name': 'SWAPS Contract', 'model': swap2}
        contract_details_types[23] = {'name': 'Token protector contract', 'model': token_protector}
        contract_details_types[24] = {'name': 'Binance Will contract', 'model': binance_lastwill}
        contract_details_types[25] = {'name': 'Binance Wallet contract (lost key)', 'model': binance_lostkey}
        contract_details_types[26] = {'name': 'Binance Deferred payment contract', 'model': binance_deffered}
        contract_details_types[27] = {'name': 'Binance MyWish ICO', 'model': binance_ico}
        contract_details_types[28] = {'name': 'Binance Token contract', 'model': binance_token}
        contract_details_types[29] = {'name': 'Binance Airdrop', 'model': binance_airdrop}
        contract_details_types[30] = {'name': 'Binance Investment Pool', 'model': binance_investment}
        contract_details_types[31] = {'name': 'Binance LostKey with tokens', 'model': binance_lostkey_tokens}
        contract_details_types[32] = {'name': 'Matic MyWish ICO', 'model': matic_ico}
        contract_details_types[33] = {'name': 'Matic Token contract', 'model': matic_token}
        contract_details_types[34] = {'name': 'Matic Airdrop', 'model': matic_airdrop}
        contract_details_types[35] = {'name': 'XinFin Token contract', 'model': xinfin_token}
        contract_details_types[36] = {'name': 'HecoChain Token contract', 'model': hecochain_token}
        contract_details_types[37] = {'name': 'HecoChain MyWish ICO', 'model': hecochain_ico}
        contract_details_types[38] = {'name': 'Moonriver Token contract', 'model': moonriver_token}
        contract_details_types[39] = {'name': 'Solana Token contract', 'model': solana_token}
        contract_details_types[40] = {'name': 'Near Token contract', 'model': near_token}
        return contract_details_types

    @classmethod
    def get_details_model(cls, contract_type):
        contract_details_types = cls.get_all_details_model()
        return contract_details_types[contract_type]['model']


class BtcKey4RSK(models.Model):
    btc_address = models.CharField(max_length=100, null=True, default=None)
    private_key = models.CharField(max_length=100, null=True, default=None)


'''
real contract to deploy to ethereum
'''


class EthContract(models.Model):
    contract = models.ForeignKey(Contract, null=True, default=None, on_delete=models.SET_NULL)
    original_contract = models.ForeignKey(
        Contract, null=True, default=None, related_name='orig_ethcontract', on_delete=models.SET_NULL
    )
    address = models.CharField(max_length=50, null=True, default=None)
    tx_hash = models.CharField(max_length=90, null=True, default=None)

    source_code = models.TextField()
    bytecode = models.TextField()
    abi = JSONField(default={})
    compiler_version = models.CharField(max_length=200, null=True, default=None)
    constructor_arguments = models.TextField()

    def __str__(self):
        return self.contract.__str__()


class CommonDetails(models.Model):

    class Meta:
        abstract = True

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    white_label = models.BooleanField(default=False)
    deploy_address = models.CharField(max_length=50, default='')
    white_label_hash = models.CharField(max_length=70, default='')

    def __str__(self):
        return self.contract.__str__()

    def compile(self, eth_contract_attr_name='eth_contract'):
        print('compiling', flush=True)
        sol_path = self.sol_path
        if getattr(self, eth_contract_attr_name):
            getattr(self, eth_contract_attr_name).delete()
        sol_path = path.join(CONTRACTS_DIR, sol_path)
        with open(path.join(sol_path, self.source_filename), 'rb') as f:
            source = f.read().decode('utf-8-sig')
        result_name = path.join(sol_path, self.result_filename)
        with open(result_name, 'rb') as f:
            result = json.loads(f.read().decode('utf-8-sig'))
        eth_contract = EthContract()
        eth_contract.source_code = source
        eth_contract.compiler_version = result['compiler']['version']
        eth_contract.abi = result['abi']
        eth_contract.bytecode = result['bytecode'][2:]
        eth_contract.contract = self.contract
        eth_contract.original_contract = self.contract
        eth_contract.save()
        setattr(self, eth_contract_attr_name, eth_contract)
        self.save()

    def deploy(self, eth_contract_attr_name='eth_contract', attempts=1):
        if self.contract.state not in ('CREATED', 'WAITING_FOR_DEPLOYMENT'):
            print('launch message ignored because already deployed', flush=True)
            take_off_blocking(self.contract.network.name)
            return
        self.compile(eth_contract_attr_name)
        eth_contract = getattr(self, eth_contract_attr_name)
        tr = abi.ContractTranslator(eth_contract.abi)
        arguments = self.get_arguments(eth_contract_attr_name)
        print('arguments', arguments, flush=True)
        eth_contract.constructor_arguments = binascii.hexlify(
            tr.encode_constructor_arguments(arguments)).decode() if arguments else ''
        eth_int = EthereumProvider().get_provider(network=self.contract.network.name)

        if self.white_label:
            if not any((self.white_label_hash, self.deploy_address)):
                print('prepare deployment of white labeled contract', flush=True)
                address = get_whitelabel_address(self.contract.id)
                self.white_label_hash = transfer_crypto(self, address)
                self.deploy_address = address
                self.save()
                print(f'white label address: {address}, transfer hash: {self.white_label_hash}', flush=True)
                return
            else:
                address = self.deploy_address
                print(f'deploying white label contract on address: {address}', flush=True)
        else:
            address = NETWORKS[self.contract.network.name]['address']

        for attempt in range(attempts):
            print(f'attempt {attempt} to get a nonce', flush=True)
            try:
                nonce_type = 'latest' if self.contract.network.name in {'XINFIN_MAINNET', 'MATIC_MAINNET'} else 'pending'
                nonce = int(eth_int.eth_getTransactionCount(address, nonce_type), 16)
                gas_price_current = self.get_gasstation_gasprice() or int(1.1 * int(eth_int.eth_gasPrice(), 16))
                break

            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            time.sleep(WEB3_ATTEMPT_COOLDOWN)
        else:
            raise Exception(f'cannot get nonce with {attempts} attempts')

        print('nonce', nonce, flush=True)
        # print('BYTECODE', eth_contract.bytecode, flush=True) print('CONTRACT CODE', eth_contract.bytecode +
        # binascii.hexlify(tr.encode_constructor_arguments(arguments)).decode() if arguments else '', flush=True)
        data = eth_contract.bytecode + (binascii.hexlify(tr.encode_constructor_arguments(arguments)).decode()
                                        if arguments else '')
        print('data =', data)
        # if arguments:
        #     data = eth_contract.bytecode + (binascii.hexlify(
        #         tr.encode_constructor_arguments(arguments)
        #     ).decode())
        # else:
        #     data = eth_contract.bytecode

        print('DATA', data, flush=True)

        gas_price_fixed = ETH_COMMON_GAS_PRICES[self.contract.network.name] * NET_DECIMALS['ETH_GAS_PRICE']
        gas_price = gas_price_current if gas_price_current < gas_price_fixed else gas_price_fixed
        chain_id = int(eth_int.eth_chainId(), 16)

        kwargs = {
            'address': address,
            'nonce': nonce,
            'gaslimit': self.get_gaslimit(),
            'value': self.get_value(),
            'contract_data': data,
            'gas_price': gas_price,
            'chain_id': chain_id
        }

        if self.white_label:
            kwargs['child_id'] = self.contract.id

        signed_data = sign_transaction(**kwargs)

        print('fields of transaction', flush=True)
        print('source', address, flush=True)
        print('gas limit', self.get_gaslimit(), flush=True)
        print('value', self.get_value(), flush=True)
        print('network', self.contract.network.name, flush=True)
        print('signed_data', signed_data, flush=True)

        for attempt in range(attempts):
            print(f'attempt {attempt} to send deploy tx', flush=True)
            try:
                tx_hash = eth_int.eth_sendRawTransaction(signed_data)
                break
            except Exception:
                print('\n'.join(traceback.format_exception(*sys.exc_info())), flush=True)
            time.sleep(WEB3_ATTEMPT_COOLDOWN)
        else:
            raise Exception(f'cannot send deploy tx with {attempts} attempts')

        eth_contract.tx_hash = tx_hash
        eth_contract.save()
        print('transaction sent', flush=True)
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
        self.contract.deployed_at = datetime.datetime.now()
        self.contract.save()
        msg = self.bot_message
        transaction.on_commit(lambda: send_message_to_subs.delay(msg, True))
        if self.contract.user.email:
            if self.contract.contract_type == 11:
                send_mail(
                    eos_account_subject,
                    eos_account_message.format(link=network_link.format(address=self.account_name),
                                               network_name=network_name), DEFAULT_FROM_EMAIL,
                    [self.contract.user.email])
            elif self.contract.contract_type == 10:
                send_mail(eos_contract_subject,
                          eos_contract_message.format(token_name=self.token_short_name, network_name=network_name),
                          DEFAULT_FROM_EMAIL, [self.contract.user.email])
            elif self.contract.contract_type == 20:
                pass
            else:
                network_id = self.contract.network.id
                types_info = AVAILABLE_CONTRACT_TYPES[network_id]
                for type_info in types_info:
                    if type_info['contract_type'] == self.contract.contract_type and \
                            type_info['contract_name'] == 'Token' and \
                            network_id in NETWORK_TYPES['mainnet']:
                        send_mail(
                            common_subject,
                            sale_message.format(
                                contract_type_name=self.contract.get_all_details_model()[self.contract.contract_type]
                                ['name'],
                                link=network_link.format(address=eth_contract.address),
                                network_name=network_name,
                            ), DEFAULT_FROM_EMAIL, [self.contract.user.email])
                        break
                else:
                    send_mail(
                        common_subject,
                        common_text.format(
                            contract_type_name=self.contract.get_all_details_model()[self.contract.contract_type]
                            ['name'],
                            link=network_link.format(address=eth_contract.address),
                            network_name=network_name,
                        ), DEFAULT_FROM_EMAIL, [self.contract.user.email])
            if not 'MAINNET' in self.contract.network.name:
                send_testnet_gift_emails.delay(self.contract.user.profile.id)
            else:
                send_promo_mainnet.delay(self.contract.user.email)

    def get_value(self):
        return 0

    def tx_failed(self, message):
        self.contract.state = 'POSTPONED'
        self.contract.postponed_at = datetime.datetime.now()
        self.contract.save()
        send_mail(postponed_subject, postponed_message.format(contract_id=self.contract.id), DEFAULT_FROM_EMAIL,
                  [EMAIL_FOR_POSTPONED_MESSAGE])
        print('contract postponed due to transaction fail', flush=True)
        take_off_blocking(self.contract.network.name, self.contract.id)
        print('queue unlocked due to transaction fail', flush=True)

    def predeploy_validate(self):
        pass

    @blocking
    def check_contract(self):
        print('checking', self.contract.name)
        tr = abi.ContractTranslator(self.eth_contract.abi)
        eth_int = EthereumProvider().get_provider(network=self.contract.network.name)
        address = self.contract.network.deployaddress_set.all()[0].address
        nonce = int(eth_int.eth_getTransactionCount(address, "pending"), 16)
        gas_price_current = self.get_gasstation_gasprice() or int(1.1 * int(eth_int.eth_gasPrice(), 16))
        gas_price_fixed = ETH_COMMON_GAS_PRICES[self.contract.network.name] * NET_DECIMALS['ETH_GAS_PRICE']
        gas_price = gas_price_current if gas_price_current < gas_price_fixed else gas_price_fixed
        chain_id = int(eth_int.eth_chainId(), 16)

        print('nonce', nonce)
        signed_data = sign_transaction(
            address,
            nonce,
            600000,
            gas_price=gas_price,
            chain_id=chain_id,
            dest=self.eth_contract.address,
            contract_data=binascii.hexlify(tr.encode_function_call('check', [])).decode(),
        )
        print('signed_data', signed_data)
        eth_int.eth_sendRawTransaction(signed_data)
        print('check ok!')

    def get_gasstation_gasprice(self):
        if self.contract.network.name == 'ETHEREUM_MAINNET':
            try:
                response = requests.get(GAS_API_URL).json()
                gas_price_current = response[SPEEDLVL] / 10
                gas_price_current = int(gas_price_current * 10**9)
                return gas_price_current
            except (requests.RequestException, KeyError):
                print('gas station api is unavailable', flush=True)

    @property
    def bot_message(self):
        eth_contracts = self.contract.ethcontract_set.all()
        hashes = [eth_contract.tx_hash for eth_contract in eth_contracts]
        link = NETWORKS.get(self.contract.network.name, '').get('link_tx', '')
        links = [f'{link.format(tx=hsh)}' for hsh in hashes]

        contract_type = self.contract.get_all_details_model()[self.contract.contract_type]['name']
        user_id = self.contract.user.id
        contract_options = []
        for option in ['white_label', 'authio', 'verification']:
            try:
                if getattr(self, option):
                    contract_options.append(option)
            except AttributeError:
                pass

        contract_options = contract_options if any(contract_options) else 'NO OPTIONS'

        message = '<a>deployed contract\nid <b>{contract_id}</b>\n<b>{network}</b>\n<b>{contract_type}</b>\n<b>{contract_options}</b>\nuser id <b>{user_id}</b></a>'.format(
            contract_id=self.contract.id,
            network=self.contract.network.name,
            contract_type=contract_type,
            contract_options=contract_options,
            user_id=user_id)

        hyperlink = '<a href="{url}">\n{text}</a>'
        for idx, link in enumerate(links):
            if link:
                message += f'{hyperlink.format(url=link, text=f"hash{idx + 1}")}'
            else:
                message += f'\n{hashes[idx]}'

        return message


@contract_details('Pizza')
class ContractDetailsPizza(CommonDetails):
    sol_path = 'lastwill/contracts/contracts/Pizza.sol'
    user_address = models.CharField(max_length=50)
    pizzeria_address = models.CharField(max_length=50, default='0x1eee4c7d88aadec2ab82dd191491d1a9edf21e9a')
    timeout = models.IntegerField(default=60 * 60)
    code = models.IntegerField()
    salt = models.CharField(max_length=len(str(2**256)))
    pizza_cost = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0)  # weis
    order_id = models.DecimalField(max_digits=50, decimal_places=0, unique=True)
    eth_contract = models.ForeignKey(EthContract, null=True, default=None, on_delete=models.SET_NULL)

    @classmethod
    def min_cost(cls):
        return 0


class Heir(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    address = models.CharField(max_length=50)
    percentage = models.IntegerField()
    email = models.CharField(max_length=200, null=True)

    def __str__(self):
        return f"{self.contract.name} for {self.email}"


class TokenHolder(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    name = models.CharField(max_length=512, null=True)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True)
    freeze_date = models.IntegerField(null=True)

    def __str__(self):
        return f"{self.name} has {self.contract.name}"


class WhitelistAddress(models.Model):
    contract = models.ForeignKey(Contract, null=True, on_delete=models.SET_NULL)
    address = models.CharField(max_length=50)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.contract.__str__()


class EOSTokenHolder(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE)
    name = models.CharField(max_length=512, null=True)
    address = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True)
    freeze_date = models.IntegerField(null=True)

    def __str__(self):
        return self.contract.__str__()
