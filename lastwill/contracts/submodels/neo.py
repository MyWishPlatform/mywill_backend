import math
import subprocess

from django.db import models
from django.core.mail import send_mail
from django.contrib.postgres.fields import JSONField
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from neo.Core.TX.Transaction import ContractTransaction
from neocore.IO.BinaryWriter import BinaryWriter
from neo.SmartContract.ContractParameterType import ContractParameterType
from neo.IO.MemoryStream import StreamManager
from neocore.Cryptography.Crypto import Crypto
from neocore.UInt160 import UInt160
from subprocess import Popen, PIPE

from lastwill.contracts.submodels.common import *
from email_messages import *
from lastwill.consts import CONTRACT_PRICE_NEO
from lastwill.settings import NEO_CLI_DIR
from jinja2 import Environment, FileSystemLoader


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
        if self.temp_directory:
            print('already compiled')
            return
        dest = create_directory(self, 'lastwill/neo3-token/*', '')[0]

        jinja_env = Environment(loader=FileSystemLoader(dest))
        token_template = jinja_env.get_template('NEP17.py')

        token_source_code = token_template.render(
            token_decimals=self.decimals,
            token_symbol=self.token_short_name,
        )
        print(token_source_code)
        token_source_code_file_name = '{name}.py'.format(name=self.token_short_name)
        token_source_code_file_path = path.join(dest, token_source_code_file_name)

        with open(token_source_code_file_path, "w") as f:
            f.write(token_source_code)

        command = "cd {dest} && venv/bin/neo3-boa {source_code_path}".format(
            dest=dest,
            source_code_path=token_source_code_file_path,
        )
        result = subprocess.run(command, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
        if result.returncode != 0:
            print(result.stdout.decode(), result.stderr.decode(), flush=True)
            raise Exception('compiler error while deploying')

        '''
        command_list = ['cd {dest}'.format(dest=dest), 'venv/bin/neo3-boa NEP17.py']
        process = Popen(command_list, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            print(stdout.decode(), stderr.decode(), flush=True)
            raise Exception('compiler error while deploying')
        '''

        '''
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
            "D_CONTINUE_MINTING": self.future_minting,
            "D_PREMINT_SCRIPT_HASHES": [],
            "D_PREMINT_AMOUNTS": []
        }}
        for th in token_holders:
            preproc_params["constants"]["D_PREMINT_SCRIPT_HASHES"].append(
                list(binascii.unhexlify(address_to_scripthash(th.address)))[::-1]
            )
            amount = [
                int(x) for x in int(th.amount).to_bytes(
                    math.floor(math.log(int(th.amount) or 1, 256)) + 1, 'little'
                )
            ]
            while len(amount) < 33:
                amount.append(0)
            preproc_params["constants"]["D_PREMINT_AMOUNTS"].append(amount)
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system("/bin/bash -c 'cd {dest} && ./2_compile_token.sh'".format(dest=dest)):
            raise Exception('compiler error while deploying')
        print('dest', dest, flush=True)
        test_neo_token_params(preproc_config, preproc_params, dest)
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))

        with open(path.join(
                dest,
                'NEP5.Contract/bin/Release/netcoreapp2.0/publish/NEP5.Contract.abi.json'
        ), 'rb') as f:
            token_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(
                dest,
                'NEP5.Contract/bin/Release/netcoreapp2.0/publish/NEP5.Contract.avm'
        ), mode='rb') as f:
            bytecode = f.read()
        with open(path.join(dest, 'NEP5.Contract/Nep5Token.cs'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
        neo_contract = NeoContract()
        neo_contract.abi = token_json
        neo_contract.bytecode = binascii.hexlify(bytecode).decode()
        neo_contract.source_code = source_code
        neo_contract.contract = self.contract
        neo_contract.original_contract = self.contract
        neo_contract.save()
        self.neo_contract = neo_contract
        self.save()
        '''

    @blocking
    @postponable
    def deploy(self, contract_params='0710', return_type='05'):
        self.compile()

        process = Popen(['./neo-cli'], stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=NEO_CLI_DIR, shell=True)
        token_nef_file_name = '{name}.nef'.format(name=self.token_short_name)
        nef_path = path.join(CONTRACTS_TEMP_DIR, str(self.temp_directory), token_nef_file_name)
        print('nef path', nef_path)
        process.stdin.write(('list address' + '\n').encode())
        process.stdin.write(('list asset' + '\n').encode())
        process.stdin.write((f'deploy {nef_path}' + '\n').encode())
        process.stdin.write(('yes' + '\n').encode())
        stdout, stderr = process.communicate()
        print('stdout', stdout)
        print('stderr', stderr)

        if process.returncode != 0:
            print(stdout.decode(), stderr.decode(), flush=True)
            raise Exception('error while deploying')
        else:
            print(stdout.decode(), stderr.decode(), flush=True)

        data = stdout.decode()
        tx_hash = data.split("Signed and relayed transaction with hash=",1)[1][:66]
        contract_address = data.split("Contract hash: ",1)[1].split('\n')[0][:42]

        neo_contract = NeoContract()
        neo_contract.contract = self.contract
        neo_contract.original_contract = self.contract
        neo_contract.tx_hash = tx_hash
        neo_contract.address = contract_address
        neo_contract.save()
        self.neo_contract = neo_contract
        self.save()
        self.initialized({})

        '''
        from_addr = NETWORKS[self.contract.network.name]['address']
        bytecode = self.neo_contract.bytecode
        neo_int = NeoInt(self.contract.network.name)
        print('from address', from_addr)
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
        print('result of send raw transaction: ', result)
        self.neo_contract.address = contract_hash
        self.neo_contract.tx_hash = tx.ToJson()['txid']
        self.neo_contract.save()
        '''

    @blocking
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
        self.contract.save()
        self.neo_contract.tx_hash = tx.ToJson()['txid']
        self.neo_contract.save()
        return

    @postponable
    @check_transaction
    def initialized(self, message):
        if self.contract.state  not in ('WAITING_FOR_DEPLOYMENT', 'ENDED'):
            return

        take_off_blocking(self.contract.network.name)

        self.contract.state = 'ACTIVE' if self.future_minting else 'ENDED'
        self.contract.deployed_at = datetime.datetime.now()
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
        if self.temp_directory:
            print('already compiled')
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
            "D_HARD_CAP_NEO": str(self.hard_cap),
            "D_PREMINT_SCRIPT_HASHES": [],
            "D_PREMINT_AMOUNTS": []
        }}
        for th in token_holders:
            preproc_params["constants"]["D_PREMINT_SCRIPT_HASHES"].append(
                list(binascii.unhexlify(address_to_scripthash(th.address)))[::-1]
            )
            amount = [
                int(x) for x in int(th.amount).to_bytes(
                    math.floor(math.log(int(th.amount) or 1, 256)) + 1, 'little'
                )
            ]
            while len(amount) < 33:
                amount.append(0)
            preproc_params["constants"]["D_PREMINT_AMOUNTS"].append(amount)
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))
        if os.system("/bin/bash -c 'cd {dest} && ./2_compile_crowdsale.sh'".format(dest=dest)):
            raise Exception('compiler error while deploying')
        print('dest', dest, flush=True)
        test_neo_ico_params(preproc_config, preproc_params, dest)
        with open(preproc_config, 'w') as f:
            f.write(json.dumps(preproc_params))

        with open(path.join(
                dest,
                'Crowdsale.Contract/bin/Release/netcoreapp2.0/publish/Crowdsale.Contract.abi.json'
        ), 'rb') as f:
            token_json = json.loads(f.read().decode('utf-8-sig'))
        with open(path.join(
                dest,
                'Crowdsale.Contract/bin/Release/netcoreapp2.0/publish/Crowdsale.Contract.avm'
        ), mode='rb') as f:
            bytecode = f.read()
        with open(path.join(dest, 'Crowdsale.Contract/Crowdsale.cs'), 'rb') as f:
            source_code = f.read().decode('utf-8-sig')
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
            return CONTRACT_PRICE_NEO['WITH_STORAGE']
        return CONTRACT_PRICE_NEO['NO_STORAGE']

    def predeploy_validate(self):
        now = timezone.now()
        if self.start_date < now.timestamp():
            raise ValidationError({'result': 1}, code=400)

    @blocking
    @postponable
    def deploy(self, contract_params='0710', return_type='05'):
        self.compile()
        from_addr = NETWORKS[self.contract.network.name]['address']
        bytecode = self.neo_contract_crowdsale.bytecode
        neo_int = NeoInt(self.contract.network.name)
        print('from address', from_addr)
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
        print('result of send raw transaction: ', result)
        self.neo_contract_crowdsale.address = contract_hash
        self.neo_contract_crowdsale.tx_hash = tx.ToJson()['txid']
        self.neo_contract_crowdsale.save()

    @blocking
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
        self.contract.save()
        self.neo_contract_crowdsale.tx_hash = tx.ToJson()['txid']
        self.neo_contract_crowdsale.save()
        return

    @postponable
    @check_transaction
    def initialized(self, message):
        if self.contract.state != 'WAITING_FOR_DEPLOYMENT':
            return

        take_off_blocking(self.contract.network.name)

        self.contract.state = 'ACTIVE'
        self.contract.deployed_at = datetime.datetime.now()
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
