import requests
import datetime
import json
from rest_framework import serializers
from .models import Contract, Heir
from rest_framework.exceptions import PermissionDenied
from lastwill.settings import SIGNER
import lastwill.check as check


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
                'balance', 'cost', 'last_check', 'next_check', 'name',
        )
        extra_kwargs = {
            'user': {'read_only': True},
            'address': {'read_only': True},
            'owner_address': {'read_only': True},
#            'state': {'read_only': True},
            'created_date': {'read_only': True},
            'source_code': {'read_only': True},
            'bytecode': {'read_only': True},
            'abi': {'read_only': True},
            'compiler_version': {'read_only': True},
            'balance': {'read_only': True},
            'cost': {'read_only': True},
            'last_check': {'read_only': True},
            'next_check': {'read_only': True},
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['state'] = 'CREATED'

        response = requests.post('http://{}/get_key/'.format(SIGNER)).content
        print(response)
        validated_data['owner_address'] = json.loads(response.decode())['addr']

        heirs = validated_data.pop('heirs')
        contract = super().create(validated_data)

        for heir_json in heirs:
            heir_json['address'] = heir_json['address'].lower()
            Heir(contract=contract, **heir_json).save() 
        return contract

    def to_representation(self, contract):
        res = super().to_representation(contract)
        heir_serializer = HeirSerializer()
        res['heirs'] = [heir_serializer.to_representation(heir) for heir in contract.heir_set.all()]
        return res

    def update(self, contract, validated_data):
        if contract.state != 'CREATED':
            raise PermissionDenied()
        if 'state' in validated_data and validated_data['state'] not in ('CREATED', 'WAITING_FOR_PAYMENT'):
            del validated_data['state']
        return super().update(contract, validated_data)

    def validate(self, data):
        if 'user_address' in data:
            check.is_address(data['user_address'])
            data['user_address'] = data['user_address'].lower()
        if 'heirs' in data and 'active_to' in data and 'check_interval' in data:
            data['cost'] = Contract.calc_cost(
                    len(data['heirs']),
                    data['active_to'].date(),
                    data['check_interval']
            )
        if 'heirs' in data:
            for heir_json in data['heirs']:
                heir_json.get('email', None) and check.is_email(heir_json['email'])
                check.is_address(heir_json['address'])
                heir_json['address'] = heir_json['address'].lower()
                check.is_percent(heir_json['percentage'])
                heir_json['percentage'] = int(heir_json['percentage'])
            check.is_sum_eq_100([h['percentage'] for h in data['heirs']])
        return data
