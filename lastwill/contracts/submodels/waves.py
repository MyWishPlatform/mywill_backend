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
from email_messages import waves_sto_subject, waves_sto_text
import json


def sign_send_waves(address_from, address_to, tx_amount):
    pub = address_from.publicKey
    pk = address_from.privateKey

    attachment = ''
    txFee = pw.DEFAULT_TX_FEE
    timestamp = int(time.time() * 1000)

    sData = b'\4' + \
            b'\2' + \
            base58.b58decode(pub) + \
            b'\0\0' + \
            struct.pack(">Q", timestamp) + \
            struct.pack(">Q", tx_amount) + \
            struct.pack(">Q", txFee) + \
            base58.b58decode(address_to) + \
            struct.pack(">H", len(attachment)) + \
            crypto.str2bytes(attachment)
    signature = crypto.sign(pk, sData)
    data = json.dumps({
        "type": 4,
        "version": 2,
        "senderPublicKey": pub.decode('utf-8'),
        "recipient": address_to.decode('utf-8'),
        "amount": tx_amount,
        "fee": txFee,
        "timestamp": timestamp,
        "attachment": base58.b58encode(crypto.str2bytes(attachment)).decode('utf-8'),
        "signature": signature.decode('utf-8'),
        "proofs": [signature.decode('utf-8')]
    })

    print('signed tx', data, flush=True)

    return pw.wrapper('/transactions/broadcast', data)


def issue_asset_waves(params, address_from):
    pub = address_from['publicKey']
    pk = address_from['privateKey']

    txFee = pw.DEFAULT_ASSET_FEE
    timestamp = int(time.time() * 1000)
    sData = b'\3' + \
            base58.b58decode(pub) + \
            struct.pack(">H", len(params['name'])) + \
            crypto.str2bytes(params['name']) + \
            struct.pack(">H", len(params['description'])) + \
            crypto.str2bytes(params['description']) + \
            struct.pack(">Q", int(params['total_supply'])) + \
            struct.pack(">B", int(params['decimals'])) + \
            b'\0' + \
            struct.pack(">Q", int(txFee)) + \
            struct.pack(">Q", timestamp)
    signature=crypto.sign(pk, sData)
    data = json.dumps({
        "senderPublicKey": pub.decode('utf-8'),
        "name": params['name'],
        "quantity": params['total_supply'],
        "timestamp": timestamp,
        "description": params['description'],
        "decimals": params['decimals'],
        "reissuable": False,
        "fee": txFee,
        "signature": signature.decode('utf-8')
    })
    return pw.wrapper('/assets/broadcast/issue', data)


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


class RideContract(EthContract):
    pass


@contract_details('Waves STO')
class ContractDetailsWavesSTO(CommonDetails):

    soft_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    hard_cap = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    asset_id = models.CharField(max_length=512, null=True, default=None)
    admin_address = models.CharField(max_length=50)
    start_date = models.DateTimeField()
    stop_date = models.DateTimeField()
    rate = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )
    temp_directory = models.CharField(max_length=36)
    cold_wallet_address = models.CharField(max_length=50, default='')
    allow_change_dates = models.BooleanField(default=False)
    whitelist = models.BooleanField(default=False)
    reused_token = models.BooleanField(default=False)
    token_description = models.CharField(max_length=1000, null=True, default=None)
    token_short_name = models.CharField(max_length=64, null=True, default=None)
    decimals = models.IntegerField(null=True, default=None)
    total_supply = models.DecimalField(
        max_digits=MAX_WEI_DIGITS, decimal_places=0, null=True
    )

    ride_contract = models.ForeignKey(
        RideContract,
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

    def predeploy_validate(self):
        now = datetime.datetime.now(timezone.utc)
        if self.start_date < now:
            raise ValidationError({'result': 1}, code=400)


    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='WAVES_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        result = int(100 * NET_DECIMALS['USDT'])
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

    def compile(self, eth_contract_attr_name='eth_contract', asset_id=''):
        print('waves sto contract compile')
        if self.temp_directory:
            print('already compiled')
            return
        dest, preproc_config = create_directory(self, sour_path='lastwill/waves-sto-contract/*')
        parsed_decimals = 10 ** int(self.decimals)
        preproc_params = {"constants": {
            # "D_MANAGEMENT_ADDRESS_PK": self.admin_address,
            "D_MANAGEMENT_ADDRESS": self.admin_address,
            "D_COLD_VAULT_ADDR": self.cold_wallet_address,
            "D_START_DATE": str(self.start_date),
            "D_FINISH_DATE": str(self.stop_date),
            "D_RATE": str(int(self.rate)),
            "D_DECIMALS_MULTIPLIER": str(int(parsed_decimals)),
            "D_WHITELIST": self.whitelist,
            "D_ASSET_ID": asset_id,
            "D_SOFT_CAP_WAVES": str(int(self.soft_cap)),
            "D_HARD_CAP_WAVES": str(int(self.hard_cap)),
            "D_MAX_INVESTMENT": str(int(self.max_wei)) if self.max_wei else '0',
            "D_MIN_INVESTMENT": str(int(self.min_wei)) if self.min_wei else '0'
    }}
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system('cd {dest} && yarn preprocess-contract'.format(dest=dest)):
            raise Exception('compiler error while deploying')

        with open(path.join(dest, 'build/sto_contract.ride'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        ride_contract = RideContract()
        ride_contract.contract = self.contract
        ride_contract.original_contract = self.contract
        ride_contract.source_code = source_code
        ride_contract.save()
        self.ride_contract = ride_contract
        self.save()

    @blocking
    @postponable
    def deploy(self):
        if NETWORKS[self.contract.network.name]['is_free']:
            pw.setNode(
                node='https://{addr}'.format(
                    addr=NETWORKS[self.contract.network.name]['host']),
                chain=NETWORKS[self.contract.network.name]['type']
            )
        else:
            pw.setNode(
                node='https://{addr}'.format(
                    addr=NETWORKS[self.contract.network.name]['host']),
                chain=NETWORKS[self.contract.network.name]['type']
            )
        pw.setOnline()

        deploy_address = pw.Address(privateKey=NETWORKS[self.contract.network.name]['private_key'])
        pubKey, privKey, address = create_waves_privkey()
        created_address = {
            'publicKey': pubKey,
            'privateKey': privKey,
            'address': address
        }
        contract_address = pw.Address(privateKey=privKey)
        print('account created', pubKey, privKey, created_address, flush=True)
        sending = sign_send_waves(deploy_address, created_address['address'], 110000000)
        #sending = deploy_address.sendWaves(contract_address, 110000000)
        print('sending', sending, flush=True)
        time.sleep(8)
        asset_id = ''
        if not self.reused_token:
            issue_attempts = 10
            for issue_attempt in range(issue_attempts):
                print('token creating attempt', issue_attempt, flush=True)
                try:
                    token_params = {
                        'name': self.token_short_name,
                        'description': self.token_description,
                        'total_supply': self.total_supply,
                        'decimals': self.decimals
                    }
                    token_tx = issue_asset_waves(token_params, created_address)
                    #token = contract_address.issueAsset(
                    #    self.token_short_name,
                    #    self.token_description,
                    #    int(self.total_supply),
                    #    int(self.decimals)
                    #)
                    print('token tx', token_tx, flush=True)

                    asset_id = token.assetId
                    asset_attempt = 0
                    while token.status() != 'Issued':
                    #for asset_attempt in range(asset_attempts)
                        if token.status() == 'Issued':
                            print('Asset {assetId} issued'.format(assetId=asset_id))
                            break
                        else:
                            asset_attempt += 1
                            print('Asset {assetId} status is {asset_status}, waiting to issue, reattempt {attempt}'
                                  .format(
                                      assetId=asset_id,
                                      asset_status=token.status(),
                                      attempt=asset_attempt,
                                      flush=True
                                  ))
                            time.sleep(10)
                            if asset_attempt >= 30:
                                raise Exception('cannot issue asset in %s attempts' % asset_attempt)
                            continue
                except KeyError:
                    print('token creation attempt {attempt} failed, retry'.format(attempt=issue_attempt))
                    pw.setOffline()
                    token_trx = contract_address.issueAsset(
                        self.token_short_name,
                        self.token_description,
                        int(self.total_supply),
                        int(self.decimals)
                    )
                    print('issueAsset trx not broadcasted', token_trx, flush=True)
                    pw.setOnline()
                    time.sleep(5)
                    if issue_attempt < issue_attempts - 1:
                        continue
                    else:
                        raise Exception('token creation error in deploying')
                break
        token_address = self.asset_id if self.reused_token else asset_id
        self.compile(asset_id=token_address)
        # pw.setOnline()
        # pw.setOffline()
        try:
            trx = contract_address.setScript(
                self.ride_contract.source_code,
            txFee=1000000,
            timestamp=0
            )
        except KeyError:
            pw.setOffline()
            trx = contract_address.setScript(
                self.ride_contract.source_code,
            txFee=1000000,
            timestamp=0
            )
            print('setScript trx not broadcasted', token_trx, flush=True)
            pw.setOffline()
        print('trx', trx, flush=True)
        if not self.asset_id:
            self.asset_id = token_address
            self.save()
        # self.ride_contract.address = address
        self.ride_contract.tx_hash = trx['id']
        self.ride_contract.save()
        self.contract.state = 'WAITING_FOR_DEPLOYMENT'
        self.contract.save()

    @blocking
    @postponable
    @check_transaction
    def msg_deployed(self, message):
        print('msg_deployed method of the ico contract')
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            take_off_blocking(self.contract.network.name)
            return
        if self.ride_contract.id == message['contractId']:
            self.contract.state = 'ACTIVE'
            self.ride_contract.address = message['address']
            self.ride_contract.save()
            self.contract.save()
            take_off_blocking(self.contract.network.name)
            if self.contract.user.email:
                network_link = NETWORKS[self.contract.network.name]['link_address']
                network_asset = NETWORKS[self.contract.network.name]['link_asset']
                network_name = MAIL_NETWORK[self.contract.network.name]
                send_mail(
                    waves_sto_subject,
                    waves_sto_text.format(
                        link1=network_asset.format(
                            asset=self.asset_id,
                        ),
                        link2=network_link.format(
                            address=self.ride_contract.address
                        ),
                        network_name=network_name
                    ),
                    DEFAULT_FROM_EMAIL,
                    [self.contract.user.email]
                )
            return

    def finalized(self, message):
        self.contract.state = 'ENDED'
        self.contract.save()

    def timesChanged(self, message):
        if 'startTime' in message and message['startTime']:
            self.start_date = message['startTime']
        if 'endTime' in message and message['endTime']:
            self.stop_date = message['endTime']
        self.save()
