from lastwill.contracts.models import ContractDetailsTokenProtector, ApprovedToken
from rest_framework import serializers
try:
    from lastwill.contracts.serializers import EthContractSerializer
except:
    pass
from rest_framework.exceptions import ValidationError
import lastwill.check as check
import datetime


class TokenProtectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsTokenProtector
        fields = ['owner_address', 'reserve_address', 'end_timestamp', 'email']

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
        if contract_details.contract.network.name in ['ETHEREUM_ROPSTEN', 'RSK_TESTNET']:
            res['eth_contract']['source_code'] = ''

        res['approved_tokens'] = []
        for token in ApprovedToken.objects.filter(contract=contract_details):
            res['approved_tokens'].append(token.address)

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
        if 'owner_address' not in contract_details or 'reserve_address' not in contract_details or 'end_timestamp' not in contract_details:
            raise ValidationError
        check.is_address(contract_details['owner_address'])
        check.is_address(contract_details['reserve_address'])
        if contract_details['end_timestamp'] < datetime.datetime.now().timestamp() + 5 * 60:
            raise ValidationError

        return contract_details

