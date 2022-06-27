import re
import traceback
from random import choices
from string import ascii_lowercase, digits
from subprocess import PIPE, STDOUT, run
from sys import byteorder
from xml.dom import ValidationErr

import base58
import near_api
from django.forms import ValidationError
from numpy import uint8

from lastwill.consts import (
    CONTRACT_PRICE_USDT, NET_DECIMALS, VERIFICATION_PRICE_USDT, WHITELABEL_PRICE_USDT)
from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.ico import AbstractContractDetailsToken
"""
24.05.2022
ПЕРВИЧНАЯ ИНТЕГРАЦИЯ NEAR БЛОКЧЕЙНА

Как выглядит флоу:
 - create contract class
 - contract calls details
 - new_account()
 - deploy() (with compile() inside)
 - initialized() (with burn_keys() and check_contract() to be 100% sure)

пусть константы пока будут тут,
чтобы было проще исправлять

TODO:
- использовать константы из consts.py и settings_local.py 
- добавить логику обработки mainnet (сейчас хардкод testnet)
"""
# макси кол-во токенов U128 - 1
# https://nomicon.io/Standards/Tokens/FungibleToken/Core#reference-level-explanation
# не умещается (((((( заменил на BigIntegerField на 2**64
MAX_WEI_DIGITS_NEAR = 2**128 - 1
# длина всех адресов 64
# https://nomicon.io/DataStructures/Account
ADDRESS_LENGTH_NEAR = 64
# регулярка для валидации имени аккаунта
# https://docs.near.org/docs/concepts/account#account-id-rules
ACCOUNT_NAME_REGEX = '^(([a-z\d]+[\-_])*[a-z\d]+\.)*([a-z\d]+[\-_])*[a-z\d]+$'
# сеть Near
NEAR_NETWORK_TYPE = "testnet"
NEAR_NETWORK_URL = "https://rpc.testnet.near.org"
# исходя из того что с лишнего газа будет сдача,
# можно просто стандартное кол-во ставить 300 TGas
NEAR_GAS_PER_TRANSACTION = 300 * 10**12
# данные нашего аккаунта в Near сети
MYWISH_ACCOUNT_NAME = "mywish.testnet"
MYWISH_PRIVATE_KEY = ""


def init_account(network: str = NEAR_NETWORK_URL,
                 account_id: str = MYWISH_ACCOUNT_NAME,
                 private_key: str = MYWISH_PRIVATE_KEY):
    """
    init_account - функция инициализации аккаунта в near-api-py
    (получает информацию о существующем аккаунте и импортирует его в соответствующий класс)

    Returns:
        near_api.account.Account : класс аккаунта из модуля
    """
    provider = near_api.providers.JsonProvider(network)
    signer = near_api.signer.Signer(
        account_id, near_api.signer.KeyPair(private_key))
    near_account = near_api.account.Account(provider, signer, account_id)
    return near_account


def generate_account_name():
    """
    generate_account_name - функция для генерации имени аккаунта.
    Дополнительно проводится проверка по регулярке с официального сайта
    Генерируется имя длиной 64 символа со строкой 'mywish' в начале

    Returns:
        str: строка с именем аккаунта
    """
    regex = re.compile(ACCOUNT_NAME_REGEX)
    result = f"mywish{''.join(choices(ascii_lowercase+digits+'-_', k=58))}"
    while not regex.match(result):
        result = f"mywish{''.join(choices(ascii_lowercase+digits+'-_', k=58))}"
    return result


class NearContract(EthContract):
    pass


@contract_details('Near Token contract')
class ContractDetailsNearToken(CommonDetails):
    # адрес владельца контракта
    admin_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR)
    # адрес аккаунта контракта
    deploy_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR)
    token_name = models.CharField(max_length=512)
    token_short_name = models.CharField(max_length=64)
    decimals = models.IntegerField()
    maximum_supply = models.BigIntegerField()
    token_type = models.CharField(max_length=32, default='NEP-141')
    future_minting = models.BooleanField(default=True)
    near_contract = models.ForeignKey(
        NearContract, null=True, default=None, on_delete=models.SET_NULL)

    @classmethod
    def min_cost(cls):
        network = Network.objects.get(name='NEAR_MAINNET')
        cost = cls.calc_cost({}, network)
        return cost

    @staticmethod
    def calc_cost(kwargs, network):
        if NETWORKS[network.name]['is_free']:
            return 0
        price = CONTRACT_PRICE_USDT['NEAR_TOKEN']
        if 'verification' in kwargs and kwargs['verification']:
            price += VERIFICATION_PRICE_USDT
        if 'white_label' in kwargs and kwargs['white_label']:
            price += WHITELABEL_PRICE_USDT
        return price * NET_DECIMALS['USDT']

    @postponable
    @blocking
    def new_account(self):
        """
        new_account - создает implicit аккаунт для пользователя,
        на который будет задеплоен контракт

        создание аккаунта будет проводиться через near-cli
        https://docs.near.org/docs/roles/integrator/implicit-accounts

        ключи аккаунта хранятся в ~/.near-credentials/{network-type}/{self.admin_address}.json
        """
        if os.system(f"/bin/bash -c 'export NEAR_ENV={NEAR_NETWORK_TYPE}'"):
            raise Exception('Error setting the Near Network env')
        try:
            account_name = generate_account_name()
            public_key = run(
                ['near', 'generate-key', f'{account_name}'], stdout=PIPE, stderr=STDOUT, check=True)
            print(f'Public key: {public_key}', flush=True)
        except Exception:
            print('Error generating key for Near Account', flush=True)
            traceback.print_exc()
        else:
            try:
                public_key = public_key.stdout.decode(
                    'utf-8').split()[4].split(':')[1]
            except IndexError:
                # срабатывает когда ключ уже сгенерирован
                public_key = public_key.stdout.decode(
                    'utf-8').split()[3].split(':')[1]
        implicit_account_name = base58.b58decode(public_key).hex()
        try:
            run(f'mv ~/.near-credentials/{NEAR_NETWORK_TYPE}/{account_name}.json ~/.near-credentials/{NEAR_NETWORK_TYPE}/{implicit_account_name}.json',
                stdout=PIPE,
                stderr=STDOUT,
                check=True,
                shell=True)
        except Exception:
            print('Error moving keys to Near Account')
            traceback.print_exc()
        print(f'Near user address {implicit_account_name}', flush=True)
        self.deploy_address = implicit_account_name
        self.save()

    def compile(self):
        dest = path.join(CONTRACTS_DIR, 'lastwill/near-contract/')
        with open(path.join(dest, 'near.token.wasm'), 'rb') as f:
            # код контракта представляет из себя побайтовый массив uint8
            bytecode = []
            while True:
                char = f.read(1)
                if not char:
                    break
                bytecode.append(uint8(int.from_bytes(char, byteorder)))
        near_contract = NearContract()
        near_contract.bytecode = bytecode
        near_contract.contract = self.contract
        near_contract.original_contract = self.contract
        near_contract.save()
        self.near_contract = near_contract
        self.save()

    @blocking
    @postponable
    def deploy(self):
        """
        deploy - функция создания аккаунта и деплоя контракта

        для создания аккаунта нужен трансфер на 182 * 10**19 монет
        для создания, деплоя и инициализации нужно 222281 * 10 ** 19 монет
        для удаления ключей нужно 40601225 * 10**12 ~ 5 * 10**19 монет
        буду отправлять 24 * 10**23, чтобы гарантированно хватило

        Raises:
            Exception:
                - если не получилось создать аккаунт с помощью transfer()
                - если завалится парсинг ключа из json файла
                - если завалится деплой контракта на аккаунт
        """
        if self.contract.state not in ('CREATED', 'WAITING_FOR_DEPLOYMENT'):
            print('launch message ignored because already deployed', flush=True)
            take_off_blocking(self.contract.network.name)
            return

        try:
            private_key = run(f'cat ~/.near-credentials/{NEAR_NETWORK_TYPE}/mywish.testnet.json',
                              stdout=PIPE,
                              stderr=STDOUT,
                              check=True,
                              shell=True)
        except Exception:
            print(f'Error getting private key from Near Account json mywish.testnet')
            traceback.print_exc()
        else:
            private_key = private_key.stdout.decode(
                'utf-8').split('"')[11].split(':')[1]
            if len(private_key) != 88:
                raise Exception(
                    f"Wrong private key provided for account mywish.testnet")
        mywish_account = init_account(private_key=private_key)

        # sending await transfer to new user account
        self.new_account()
        try:
            tx_account_hash = mywish_account.send_money(
                self.deploy_address, 24 * 10**23)
            print(f'account creation:\n{tx_account_hash}\n', flush=True)
        except Exception:
            traceback.print_exc()

        try:
            private_key = run(f'cat ~/.near-credentials/{NEAR_NETWORK_TYPE}/{self.deploy_address}.json',
                              stdout=PIPE,
                              stderr=STDOUT,
                              check=True,
                              shell=True)
        except Exception:
            print(
                f'Error getting private key from Near Account json {self.deploy_address}')
            traceback.print_exc()
        else:
            private_key = private_key.stdout.decode(
                'utf-8').split('"')[11].split(':')[1]
            if len(private_key) != 88:
                raise Exception(
                    f"Wrong private key provided for account {self.deploy_address}")
        near_account = init_account(
            network=NEAR_NETWORK_URL, account_id=self.deploy_address, private_key=private_key)

        self.compile()
        args = {
            "owner_id": self.admin_address,
            "total_supply": str(self.maximum_supply),
            "metadata": {
                "spec": "ft-1.0.0",
                "name": self.token_name,
                "symbol": self.token_short_name,
                "decimals": self.decimals
            }
        }
        print(args, flush=True)

        try:
            tx_deploy_hash = near_account.deploy_and_init_contract(contract_code=self.near_contract.bytecode,
                                                                   args=args,
                                                                   gas=near_api.account.DEFAULT_ATTACHED_GAS,
                                                                   init_method_name="new")
        except Exception:
            traceback.print_exc()
        else:
            tx_deploy_hash = tx_deploy_hash['transaction_outcome']['id']
        print(f'tx_hash: {tx_deploy_hash}', flush=True)
        self.near_contract.tx_hash = tx_deploy_hash
        self.near_contract.save()
        self.contract.state = 'WAITING_ACTIVATION'
        self.contract.save()

    def burn_keys(self):
        """
        burn_keys - функция для сжигания ключей после деплоя контракта

        Raises:
            ValidationError: завалился парсинг ключа из json файла
            ValidationError: не получилось сжечь ключи
        """
        try:
            keys = run(f'cat ~/.near-credentials/{NEAR_NETWORK_TYPE}/{self.deploy_address}.json',
                       stdout=PIPE,
                       stderr=STDOUT,
                       check=True,
                       shell=True)
        except Exception:
            print('Error getting keys from Near Account json')
            traceback.print_exc()
        else:
            private_key = keys.stdout.decode(
                'utf-8').split('"')[11].split(':')[1]
            public_key = keys.stdout.decode(
                'utf-8').split('"')[7].split(':')[1]
            if len(private_key) != 88:
                raise ValidationError(
                    f"Wrong private key provided for account {self.deploy_address}")
            if len(public_key) != 44:
                raise ValidationError(
                    f"Wrong public key provided for account {self.deploy_address}")

        near_account = init_account(
            network=NEAR_NETWORK_URL, account_id=self.deploy_address, private_key=private_key)

        try:
            near_account.delete_access_key(
                public_key=near_account.signer.public_key)
        except Exception:
            traceback.print_exc()

    def check_contract(self):
        """
        check_contract - функция проверки валидность контракта
        и успешность транзакции сжигания ключей

        Raises:
            ValidationError: получен неверный ключ
            ValidationError: контракт не совпадает
            ValidationError: ключи не сожглись
        """
        try:
            keys = run(f'cat ~/.near-credentials/{NEAR_NETWORK_TYPE}/{self.deploy_address}.json',
                       stdout=PIPE,
                       stderr=STDOUT,
                       check=True,
                       shell=True)
        except Exception:
            print('Error getting keys from Near Account json')
            traceback.print_exc()
        else:
            private_key = keys.stdout.decode(
                'utf-8').split('"')[11].split(':')[1]
            if len(private_key) != 88:
                raise ValidationError(
                    f"Wrong private key provided for account {self.deploy_address}")

        near_account = init_account(
            network=NEAR_NETWORK_URL, account_id=self.deploy_address, private_key=private_key)

        try:
            result = near_account.function_call(contract_id=self.deploy_address,
                                                method_name='ft_metadata',
                                                args={},
                                                gas=near_api.account.DEFAULT_ATTACHED_GAS)
        except Exception:
            print(
                f'Error function call ft_metadata() for {near_account.account_id}')
            traceback.print_exc()
        else:
            if not (result['name'] == self.token_name and result['symbol'] == self.token_short_name and
                    result['decimals'] == self.decimals):
                raise ValidationError(
                    f"Contract metadata is corrupted on account {self.deploy_address}")

        print(
            f'Contract {self.deploy_address} checked successfully', flush=True)

    @postponable
    @blocking
    def initialized(self):
        """
        initialized - финальная функция,
        которая сжигает ключи и 
        проверяет, что контракт был успешно задеплоен

        затем отправляет сообщение пользователю и боту
        об успешности операции
        """
        if self.contract.state not in ('WAITING_ACTIVATION'):
            take_off_blocking(self.contract.network.name)
            return

        self.burn_keys()
        self.check_contract()

        self.contract.state = 'ACTIVE' if self.future_minting else 'DONE'
        self.contract.deployed_at = datetime.datetime.now()
        self.contract.save()
        if self.contract.user.email:
            send_mail(common_subject, near_token_text.format(addr=self.deploy_address), DEFAULT_FROM_EMAIL,
                      [self.contract.user.email])
            if not 'MAINNET' in self.contract.network.name:
                send_testnet_gift_emails.delay(self.contract.user.profile.id)
            else:
                send_promo_mainnet.delay(self.contract.user.email)

        msg = self.bot_message
        transaction.on_commit(lambda: send_message_to_subs.delay(msg, True))

    @postponable
    def msg_deployed(self, message):
        # deprecated
        return
