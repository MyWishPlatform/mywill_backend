from rest_framework import serializers
from .models import Contract, Heir
from rest_framework.exceptions import PermissionDenied

class HeirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Heir
        fields = ('address', 'email', 'percentage')

class ContractSerializer(serializers.ModelSerializer):
    heirs = serializers.JSONField(write_only=True)

    class Meta:
        model = Contract
        fields = ('id', 'user', 'address', 'owner_address', 'user_address',
                'state', 'created_date', 'source_code', 'bytecode', 'abi',
                'compiler_version', 'heirs', 'check_interval', 'active_to',
        )
        extra_kwargs = {
            'user': {'read_only': True},
            'address': {'read_only': True},
            'owner_address': {'read_only': True},
            'state': {'read_only': True},
            'created_date': {'read_only': True},
            'source_code': {'read_only': True},
            'bytecode': {'read_only': True},
            'abi': {'read_only': True},
            'compiler_version': {'read_only': True},
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        heirs = validated_data.pop('heirs')
        contract = super().create(validated_data)
        for serialized_heir in heirs:
            Heir(contract=contract, **serialized_heir).save() 
        return contract

    def to_representation(self, contract):
        res = super().to_representation(contract)
        heir_serializer = HeirSerializer()
        res['heirs'] = [heir_serializer.to_representation(heir) for heir in contract.heir_set.all()]
        return res

    def update(self, *args):
        raise PermissionDenied()
