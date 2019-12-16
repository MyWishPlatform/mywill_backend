from lastwill.contracts.models import ContractDetailsTokenProtector
from rest_framework import serializers
from lastwill.contracts.serializers import EthContractSerializer
from rest_framework.exceptions import ValidationError
import lastwill.check as check
import datetime


class TokenProtectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsTokenProtector
        fields = ['user_address', 'reverse_address', 'end_date']

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
        if 'user_address' not in contract_details or 'reverse_address' not in contract_details or 'end_date' not in contract_details:
            raise ValidationError
        check.is_address(contract_details['user_address'])
        check.is_address(contract_details['reverse_address'])
        if contract_details['end_date'] < datetime.datetime.now().timestamp() + 5 * 60:
            raise ValidationError

        return contract_details

