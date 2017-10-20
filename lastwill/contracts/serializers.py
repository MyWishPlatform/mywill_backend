import requests
import datetime
import json
from rest_framework import serializers
from django.apps import apps
from .models import Contract, Heir, ContractDetailsLastwill, ContractDetailsDelayedPayment
from rest_framework.exceptions import PermissionDenied
from lastwill.settings import SIGNER
import lastwill.check as check
from lastwill.contracts.types import contract_types
from lastwill.settings import ORACLIZE_PROXY

class HeirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Heir
        fields = ('address', 'email', 'percentage')

class ContractSerializer(serializers.ModelSerializer):
#    heirs = serializers.JSONField(write_only=True)
    contract_details = serializers.JSONField(write_only=True)

    class Meta:
        model = Contract
        fields = ('id', 'user', 'address', 'owner_address',
                'state', 'created_date', 'source_code', 'bytecode', 'abi',
                'compiler_version', 'balance', 'cost', 'name',
                'contract_type', 'contract_details',
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

        details_serializer = self.get_details_serializer(validated_data['contract_type'])(context=self.context) 
        details_serializer.validate(validated_data)
        contract_details = validated_data.pop('contract_details')
        
        contract = super().create(validated_data)
        
        details_serializer.create(contract, contract_details)
        return contract


    def to_representation(self, contract):
        res = super().to_representation(contract)
        res['contract_details'] = self.get_details_serializer(contract.contract_type)(context=self.context).to_representation(contract.get_details())
        return res

    def update(self, contract, validated_data):
        if contract.state != 'CREATED':
            raise PermissionDenied()
        if 'state' in validated_data and validated_data['state'] not in ('CREATED', 'WAITING_FOR_PAYMENT'):
            del validated_data['state']
        return super().update(contract, validated_data)

    def get_details_serializer(self, contract_type):
        details_serializers = [
            ContractDetailsLastwillSerializer,
            ContractDetailsLastwillSerializer,
            ContractDetailsDelayedPaymentSerializer,
        ]
        return details_serializers[contract_type]

    
class ContractDetailsLastwillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsLastwill
        fields = ('user_address', 'active_to', 'check_interval', 'last_check', 'next_check')
        extra_kwargs = {
            'last_check': {'read_only': True},
            'next_check': {'read_only': True},
        }

    def to_representation(self, contract_details_lastwill):
        res = super().to_representation(contract_details_lastwill)
        heir_serializer = HeirSerializer()
        res['heirs'] = [heir_serializer.to_representation(heir) for heir in contract_details_lastwill.contract.heir_set.all()]
        return res

    def create(self, contract, contract_details):
        heirs = contract_details.pop('heirs')
        for heir_json in heirs:
            heir_json['address'] = heir_json['address'].lower()
            kwargs = heir_json.copy()
            kwargs['contract'] = contract
            Heir(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().create(kwargs)

    def validate(self, data):
        details = data['contract_details']
        assert('user_address' in details and'heirs' in details and 'active_to' in details and 'check_interval' in details)
        check.is_address(details['user_address'])
        details['user_address'] = details['user_address'].lower()
        details['active_to'] = datetime.datetime.strptime(details['active_to'], '%Y-%m-%d %H:%M')
        data['cost'] = self.Meta.model.calc_cost({
                'heirs_num': len(details['heirs']),
                'active_to': details['active_to'].date(),
                'check_interval': details['check_interval']
        })
        for heir_json in details['heirs']:
            heir_json.get('email', None) and check.is_email(heir_json['email'])
            check.is_address(heir_json['address'])
            heir_json['address'] = heir_json['address'].lower()
            check.is_percent(heir_json['percentage'])
            heir_json['percentage'] = int(heir_json['percentage'])
        check.is_sum_eq_100([h['percentage'] for h in details['heirs']])
        return data

class ContractDetailsDelayedPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsDelayedPayment
        fields = ('user_address', 'date', 'recepient_address', 'recepient_email')

    def create(self, contract, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().create(kwargs)

    def validate(self, data):
        data['cost'] = self.Meta.model.calc_cost(dict())
        return data
