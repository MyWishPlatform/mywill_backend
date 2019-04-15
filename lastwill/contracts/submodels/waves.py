import datetime
import base58
import time

from ethereum import abi
import pywaves as pw
import pywaves.crypto as crypto
import axolotl_curve25519 as curve
import struct

from django.db import models
from django.core.mail import send_mail, EmailMessage
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from lastwill.contracts.submodels.common import *
from lastwill.consts import NET_DECIMALS


def create_waves_privkey(publicKey='', privateKey='', seed='', nonce=0):
    if not publicKey and not privateKey and not seed:
        wordCount = 2048
        words = []
        for i in range(5):
            r = crypto.bytes2str(os.urandom(4))
            x = (ord(r[3])) + (ord(r[2]) << 8) + (ord(r[1]) << 16) + (
                        ord(r[0]) << 24)
            w1 = x % wordCount
            w2 = ((int(x / wordCount) >> 0) + w1) % wordCount
            w3 = ((int(
                (int(x / wordCount) >> 0) / wordCount) >> 0) + w2) % wordCount
            words.append(pw.address.wordList[w1])
            words.append(pw.address.wordList[w2])
            words.append(pw.address.wordList[w3])
        seed = ' '.join(words)
    if publicKey:
        pubKey = base58.b58decode(publicKey)
        privKey = ""
    else:
        seedHash = crypto.hashChain(
            struct.pack(">L", nonce) + crypto.str2bytes(seed))
        accountSeedHash = crypto.sha256(seedHash)
        if not privateKey:
            privKey = curve.generatePrivateKey(accountSeedHash)
        else:
            privKey = base58.b58decode(privateKey)
        pubKey = curve.generatePublicKey(privKey)
    unhashedAddress = chr(1) + str(pw.CHAIN_ID) + crypto.hashChain(pubKey)[
                                                       0:20]
    addressHash = crypto.hashChain(crypto.str2bytes(unhashedAddress))[0:4]
    address = base58.b58encode(
        crypto.str2bytes(unhashedAddress + addressHash))
    publicKey = base58.b58encode(pubKey)
    if privKey != "":
        privateKey = base58.b58encode(privKey)
    return publicKey, privateKey, address


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
            "D_RATE": str(int(self.rate)),
            "D_WHITELIST": self.whitelist,
            "D_ASSET_ID": self.token_address,
            "D_SOFT_CAP_WAVES": str(int(self.soft_cap)),
            "D_HARD_CAP_WAVES": str(int(self.hard_cap))
    }}
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && yarn preprocess-contract'.format(dest=dest)):
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

    @blocking
    @postponable
    def deploy(self):
        self.compile()
        if NETWORKS[self.contract.network.name]['is_free']:
            pw.setNode(
                node='https://{addr}'.format(
                    addr=NETWORKS[self.contract.network.name]['host']),
                chain='testnet'
            )
        else:
            pw.setNode(
                node='https://{addr}'.format(
                    addr=NETWORKS[self.contract.network.name]['host']),
                chain='mainnet'
            )

        deploy_address = pw.Address(privateKey=NETWORKS[self.contract.network.name]['private_key'])
        pubKey, privKey, address = create_waves_privkey()
        contract_address = pw.Address(privateKey=privKey)
        print('account created', pubKey, privKey, address, flush=True)
        sending = deploy_address.sendWaves(contract_address, 10000000)
        print('sending', sending, flush=True)
        time.sleep(8)
        pw.setOnline()
        trx = contract_address.setScript(
            self.waves_contract.source_code,
            txFee=1000000,
            timestamp=0
        )
        print('trx', trx, flush=True)
        self.waves_contract.address = address
        self.waves_contract.tx_hash = trx['id']
        self.waves_contract.save()

    @blocking
    @postponable
    def msg_deployed(self, message):
        print('msg_deployed method of the ico contract')
        address = NETWORKS[self.contract.network.name]['address']
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            take_off_blocking(self.contract.network.name)
            return
        if self.waves_contract.id == message['contractId']:
            self.contract.state = 'ACTIVE'
            self.contract.save()
            return
