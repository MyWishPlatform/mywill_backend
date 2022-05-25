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
    # address - адрес деплоя
    # owner - адрес внутри контракта
    # user - адрес подписи (должен совпадать с address или быть его родительским аккаунтом)
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
    token_type = models.CharField(max_length=32, default='NEP-141')
    maximum_supply = models.DecimalField(max_digits=MAX_WEI_DIGITS_NEAR, decimal_places=0, null=True)
    eth_contract_token = models.ForeignKey(
        EthContract,
        null=True,
        default=None,
        related_name='near_token_details_token',
        on_delete=models.SET_NULL
    )
    
    def compile(self, eth_contract_attr_name='eth_contract_token'):
        pass

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
