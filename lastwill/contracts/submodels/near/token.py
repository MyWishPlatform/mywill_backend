from subprocess import run, STDOUT, PIPE, CalledProcessError
from numpy import uint8
from sys import byteorder
import near_api
from lastwill.contracts.submodels.common import *
from lastwill.contracts.submodels.ico import AbstractContractDetailsToken

"""
24.05.2022
ПЕРВИЧНАЯ ИНТЕГРАЦИЯ NEAR БЛОКЧЕЙНА

пусть константы пока будут тут,
чтобы было проще исправлять
"""
# макси кол-во токенов U128 - 1
# https://nomicon.io/Standards/Tokens/FungibleToken/Core#reference-level-explanation
MAX_WEI_DIGITS_NEAR = 2 ** 128 - 1
# длина всех адресов 64
# https://nomicon.io/DataStructures/Account
ADDRESS_LENGTH_NEAR = 64

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
    original_contract = models.ForeignKey(
        BaseContract, null=True, default=None, related_name='orig_ethcontract'
    )
    address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, null=True, default=None)


@contract_details('Near Token contract')
class ContractDetailsNearToken(AbstractContractDetailsToken):
    admin_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR)
    deploy_address = models.CharField(max_length=ADDRESS_LENGTH_NEAR, default='')
    token_type = models.CharField(max_length=32, default='NEP-141')
    maximum_supply = models.DecimalField(max_digits=MAX_WEI_DIGITS_NEAR, decimal_places=0, null=True)
    near_contract = models.ForeignKey(
        NearContract,
        null=True,
        default=None,
        related_name='near_token_details',
        on_delete=models.SET_NULL
    )
    
    def compile(self):
        if self.temp_directory:
            print('Near Token is already compiled')
            return
        dest = create_directory(self, sour_path='lastwill/near_token/*', config_name=None)
        try:
            # https://docs.python.org/3/library/subprocess.html
            result = run(['cd', f'{dest}', '&&', 'make'], stdout=PIPE, stderr=STDOUT, check=True)
        except:
            raise CalledProcessError(f'Near Token compile error\n', result.stdout.decode('utf-8'))
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
