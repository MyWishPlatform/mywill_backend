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
NEAR_NETWORK_URL = "https://rpc.testnet.near.org"
# исходя из того что с лишнего газа будет сдача,
# можно просто стандартное кол-во ставить 300 TGas
NEAR_GAS_PER_TRANSACTION = 300 * 10**12
# данные нашего аккаунта в Near сети
MYWISH_ACCOUNT_NAME = "mywish.testnet"
MYWISH_PRIVATE_KEY = ""


def init_mywish_account():
    """
    init_mywish_account - функция инициализации аккаунта в near-api-py
    (получает информацию о существующем аккаунте и импортирует его в соответствующий класс)
    
    Returns:
        near_api.account.Account : класс аккаунта из модуля
    """
    provider = near_api.providers.JsonProvider(NEAR_NETWORK_URL)
    signer = near_api.signer.Signer(MYWISH_ACCOUNT_NAME, near_api.signer.KeyPair(MYWISH_PRIVATE_KEY))
    mywish_account = near_api.account.Account(provider, signer, MYWISH_ACCOUNT_NAME)
    return mywish_account


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
        near_network_type = 'testnet'
        if os.system(f"/bin/bash -c 'export NEAR_ENV={near_network_type}'"):
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
            run(f'mv ~/.near-credentials/{near_network_type}/{account_name}.json ~/.near-credentials/{near_network_type}/{implicit_account_name}.json',
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
    def deploy(self, attempts: int = 1):
        """
        deploy _summary_
        
        для создания аккаунта нужен трансфер на 182 * 10**19 монет
        для создания, деплоя и инициализации нужно 222281 * 10 ** 19 монет
        """
        mywish_account = init_mywish_account()
        # sending await transfer to new user account
        for attempt in range(attempts):
            print(f'attempt {attempt} to send account creation tx', flush=True)
            try:
                tx_account_hash = mywish_account.send_money(self.admin_address, 222281 * 10**19)
                print(f'account creation:\n{tx_account_hash}\n', flush=True)
                break
            except Exception:
                traceback.print_exc()
            time.sleep(WEB3_ATTEMPT_COOLDOWN)
        else:
            raise Exception(f'cannot send account creation tx with {attempts} attempts')

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
        tx_deploy_hash = mywish_account.deploy_and_init_contract_async(contract_code=self.near_contract.bytecode,
                                                                       args=args,
                                                                       gas=near_api.account.DEFAULT_ATTACHED_GAS,
                                                                       init_method_name="new")
        print(f'tx_hash: {tx_deploy_hash}', flush=True)
        self.near_contract.tx_hash = tx_deploy_hash
        self.near_contract.address = self.token_account
        self.near_contract.save()
        self.contract.state = 'WAITING_FOR_DEPLOYMENT'
        self.contract.save()

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        pass

    def check_contract(self):
        pass

    def initialized(self, message):
        pass
