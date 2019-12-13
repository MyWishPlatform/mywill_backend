from lastwill.contracts.models import ContractDetailsTokenProtector
from rest_framework import serializers
from lastwill.contracts.serializers import EthContractSerializer


class TokenSaverSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsTokenProtector
        fields = '__all__'

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
        if contract_details.contract.network.name in ['ETHEREUM_ROPSTEN', 'RSK_TESTNET']:
            res['eth_contract']['source_code'] = ''
        return res

    def create(self, contract, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().create(kwargs)

    def update(self, contract, details, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().update(details, kwargs)

    def validate(self, contract_details):

        pass
