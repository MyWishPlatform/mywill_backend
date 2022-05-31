import re
import traceback
from random import choices
from string import ascii_lowercase, digits
from subprocess import PIPE, STDOUT, run
from sys import byteorder

import base58
import near_api
from numpy import uint8

from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.ico import AbstractContractDetailsToken
from lastwill.settings import WEB3_ATTEMPT_COOLDOWN
"""
24.05.2022
ПЕРВИЧНАЯ ИНТЕГРАЦИЯ NEAR БЛОКЧЕЙНА

Как выглядит флоу:
- мы создаем аккаунт пользователю в Near
- деплоим на этот аккаунт контракт
- генерируем ключи для пользователя и передаем их
- свои ключи сжигаем

пусть константы пока будут тут,
чтобы было проще исправлять
"""
# макси кол-во токенов U128 - 1
# https://nomicon.io/Standards/Tokens/FungibleToken/Core#reference-level-explanation
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
    signer = near_api.signer.Signer(account_id, near_api.signer.KeyPair(private_key))
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


class BaseContract(Contract):
    """
    BaseContract - наследник базового контракта Contract из common.py

    Args:
        address - адрес деплоя
        owner - адрес внутри контракта
        user - адрес подписи (должен совпадать с address или быть его родительским аккаунтом)
    """
    address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, null=True, default=None)
    owner_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, null=True, default=None)
    user_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, null=True, default=None)


class NearContract(EthContract):
    contract = models.ForeignKey(BaseContract, null=True, default=None)
    original_contract = models.ForeignKey(BaseContract, null=True, default=None, related_name='orig_ethcontract')
    # адрес контракта
    address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, null=True, default=None)


@contract_details('Near Token contract')
class ContractDetailsNearToken(AbstractContractDetailsToken):
    # адрес пользователя в сети Near
    admin_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR)
    # адрес деплоя
    deploy_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, default='')
    maximum_supply = models.DecimalField(max_digits=MAX_WEI_DIGITS_NEAR, decimal_places=0, null=True)
    near_contract = models.ForeignKey(NearContract,
                                      null=True,
                                      default=None,
                                      related_name='near_token_details',
                                      on_delete=models.SET_NULL)

    @blocking
    @postponable
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
            public_key = run(['near', 'generate-key', f'{account_name}'], stdout=PIPE, stderr=STDOUT, check=True)
            print(f'Public key: {public_key}', flush=True)
        except Exception:
            print('Error generating key for Near Account', flush=True)
            traceback.print_exc()
        else:
            public_key = public_key.stdout.decode('utf-8').split()[4].split(':')[1]
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
        self.admin_address = implicit_account_name
        self.save()

    def compile(self):
        if self.temp_directory:
            print('Near Token is already compiled', flush=True)
            return
        dest, _ = create_directory(self, sour_path='lastwill/near_token/*', config_name=None)
        try:
            # https://docs.python.org/3/library/subprocess.html
            result = run(['cd', f'{dest}', '&&', 'make'], stdout=PIPE, stderr=STDOUT, check=True)
            print('Near Token compiled successfully', flush=True)
        except Exception:
            print('Near Token compilation error', flush=True)
            traceback.print_exc()
        with open(path.join(dest, 'near.token/near.token.wasm'), 'rb') as f:
            # код контракта представляет из себя побайтовый массив uint8
            bytecode = []
            while True:
                char = f.read(1)
                if not char:
                    break
                bytecode.append(uint8(int.from_bytes(char, byteorder)))
        with open(path.join(dest, 'near.token.rs'), 'rb') as f:
            # не уверен нужен ли вообще, но пока пусть будет так
            source_code = f.read().decode('utf-8-sig')
        near_contract = NearContract()
        near_contract.bytecode = bytecode
        near_contract.source_code = source_code
        near_contract.contract = self.contract
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
        mywish_account = init_account()
        # sending await transfer to new user account
        self.new_account()
        try:
            tx_account_hash = mywish_account.send_money(self.admin_address, 23 * 10**23)
            print(f'account creation:\n{tx_account_hash}\n', flush=True)
        except Exception:
            traceback.print_exc()

        try:
            private_key = run(f'cat ~/.near-credentials/{NEAR_NETWORK_TYPE}/{self.admin_address}.json',
                              stdout=PIPE,
                              stderr=STDOUT,
                              check=True,
                              shell=True)
        except Exception:
            print('Error getting private key from Near Account json')
            traceback.print_exc()
        else:
            private_key = private_key.stdout.decode('utf-8').split('"')[11].split(':')[1]
            if len(private_key) != 88:
                raise Exception("Wrong private key provided")
        near_account = init_account(network=NEAR_NETWORK_URL, account_id=self.admin_address, private_key=private_key)

        self.compile()
        args = {
            "owner_id": self.near_contract.contract.owner_address,
            "total_supply": f"{self.maximum_supply}",
            "metadata": {
                "spec": "ft-1.0.0",
                "name": f"{self.token_name}",
                "symbol": f"{self.token_short_name}",
                "decimals": self.decimals
            }
        }
        print(args, flush=True)

        try:
            tx_deploy_hash = near_account.deploy_and_init_contract_async(contract_code=self.near_contract.bytecode,
                                                                         args=args,
                                                                         gas=near_api.account.DEFAULT_ATTACHED_GAS,
                                                                         init_method_name="new")
        except Exception:
            traceback.print_exc()
        print(f'tx_hash: {tx_deploy_hash}', flush=True)
        self.near_contract.tx_hash = tx_deploy_hash
        self.near_contract.save()
        self.contract.state = 'WAITING_FOR_DEPLOYMENT'
        self.contract.save()

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        pass

    @postponable
    @check_transaction
    def burn_keys(self, message):
        """
        burn_keys - функция для сжигания ключей после деплоя контракта

        Args:
            message (_type_): _description_

        Raises:
            Exception:
                - если завалится парсинг ключа из json файла
                - если сжигание ключей не пройдет
        """
        if self.contract.state not in ('ACTIVE', 'ENDED'):
            print('burning keys message ignored because state is not ACTIVE or ENDED', flush=True)
            take_off_blocking(self.contract.network.name)
            return
        try:
            public_key = run(f'cat ~/.near-credentials/{NEAR_NETWORK_TYPE}/{self.admin_address}.json',
                             stdout=PIPE,
                             stderr=STDOUT,
                             check=True,
                             shell=True)
        except Exception:
            print('Error getting public key from Near Account json', flush=True)
            traceback.print_exc()
        else:
            public_key = public_key.stdout.decode('utf-8').split('"')[7].split(':')[1]
            if len(public_key) != 44:
                raise Exception("Wrong public key provided")

        try:
            run(['near', 'delete-key', f'{self.admin_address}', f'{public_key}'],
                stdout=PIPE,
                stderr=STDOUT,
                check=True)
        except Exception:
            print(f'Error burning key on Near Account {self.admin_address}', flush=True)
            traceback.print_exc()

        print(f'Near Account {self.admin_address} keys burnt', flush=True)

    def check_contract(self):
        pass

    def initialized(self, message):
        pass
