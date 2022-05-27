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
    address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, null=True, default=None)


@contract_details('Near Token contract')
class ContractDetailsNearToken(AbstractContractDetailsToken):
    admin_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR)
    deploy_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, default='')
    token_type = models.CharField(max_length=32, default='NEP-141')
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
        except Exception:
            print('Error generating key for Near Account')
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
        self.admin_address = implicit_account_name
        self.save()

    def compile(self):
        if self.temp_directory:
            print('Near Token is already compiled')
            return
        dest, _ = create_directory(self, sour_path='lastwill/near_token/*', config_name=None)
        try:
            # https://docs.python.org/3/library/subprocess.html
            result = run(['cd', f'{dest}', '&&', 'make'], stdout=PIPE, stderr=STDOUT, check=True)
        except Exception:
            print('Near Token compilation error')
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
        near_contract.abi = abi
        near_contract.bytecode = bytecode
        near_contract.source_code = source_code
        near_contract.contract = self.contract
        near_contract.save()
        self.near_contract = near_contract
        self.save()

    @blocking
    @postponable
    def deploy(self):
        pass

    @postponable
    @check_transaction
    def msg_deployed(self, message):
        pass

    def check_contract(self):
        pass

    def initialized(self, message):
        pass
