import requests
import datetime
import json
import random
from rest_framework import serializers
from django.apps import apps
from django.db import transaction
from .models import Contract, Heir, ContractDetailsLastwill, ContractDetailsDelayedPayment, ContractDetailsLostKey, ContractDetailsPizza, contract_details_types, EthContract, ContractDetailsICO, TokenHolder
from rest_framework.exceptions import PermissionDenied
from lastwill.settings import SIGNER
import lastwill.check as check
from lastwill.settings import ORACLIZE_PROXY

class HeirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Heir
        fields = ('address', 'email', 'percentage')


class TokenHolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenHolder
        fields = ('address', 'amount', 'freeze_date', 'name')

    def to_representation(self, th):
        res = super().to_representation(th)
        res['amount'] = int(res['amount'])
        return res


class ContractSerializer(serializers.ModelSerializer):
    contract_details = serializers.JSONField(write_only=True)

    class Meta:
        model = Contract
        fields = ('id', 'user', 'owner_address',
                'state', 'created_date',
                'balance', 'cost', 'name',
                'contract_type', 'contract_details',
        )
        extra_kwargs = {
            'user': {'read_only': True},
            'owner_address': {'read_only': True},
            'created_date': {'read_only': True},
            'balance': {'read_only': True},
            'cost': {'read_only': True},
            'last_check': {'read_only': True},
            'next_check': {'read_only': True},
        }

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        if validated_data.get('state') not in ('CREATED', 'WAITING_FOR_PAYMENT'):
            validated_data['state'] = 'CREATED'
        
#        response = requests.post('http://{}/get_key/'.format(SIGNER)).content
#        print(response)
#        validated_data['owner_address'] = json.loads(response.decode())['addr']

        contract_type = validated_data['contract_type']
        details_serializer = self.get_details_serializer(contract_type)(context=self.context) 
        contract_details = validated_data.pop('contract_details')
        details_serializer.validate(contract_details)
        validated_data['cost'] = Contract.get_details_model(contract_type).calc_cost(contract_details)
        transaction.set_autocommit(False)
        try:
            contract = super().create(validated_data)
            details_serializer.create(contract, contract_details)
        except:
            transaction.rollback()
            raise
        else:
            transaction.commit()
        finally:
            transaction.set_autocommit(True)
        return contract

    def to_representation(self, contract):
        res = super().to_representation(contract)
        res['contract_details'] = self.get_details_serializer(contract.contract_type)(context=self.context).to_representation(contract.get_details())
        return res

    def update(self, contract, validated_data):
        validated_data.pop('contract_type', None)
        if contract.state != 'CREATED':
            raise PermissionDenied()
        if 'state' in validated_data and validated_data['state'] not in ('CREATED', 'WAITING_FOR_PAYMENT'):
            del validated_data['state']

        contract_type = contract.contract_type
        contract_details = validated_data.pop('contract_details', None)
        if contract_details:
            details_serializer = self.get_details_serializer(contract_type)(context=self.context) 
            details_serializer.validate(contract_details)
            validated_data['cost'] = contract.get_details().calc_cost(contract_details)
            details_serializer.update(contract, contract.get_details(), contract_details)

        return super().update(contract, validated_data)

    def get_details_serializer(self, contract_type):
        return [
            ContractDetailsLastwillSerializer,
            ContractDetailsLostKeySerializer,
            ContractDetailsDelayedPaymentSerializer,
            ContractDetailsPizzaSerializer,
            ContractDetailsICOSerializer,
        ][contract_type]


class EthContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = EthContract
        fields = ('address', 'source_code', 'abi', 'bytecode', 'compiler_version')


class ContractDetailsLastwillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsLastwill
        fields = ('user_address', 'active_to', 'check_interval', 'last_check', 'next_check')
        extra_kwargs = {
            'last_check': {'read_only': True},
            'next_check': {'read_only': True},
        }

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        heir_serializer = HeirSerializer()
        res['heirs'] = [heir_serializer.to_representation(heir) for heir in contract_details.contract.heir_set.all()]
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
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

    def update(self, contract, details, contract_details):
        contract.heir_set.all().delete()
        heirs = contract_details.pop('heirs')
        for heir_json in heirs:
            heir_json['address'] = heir_json['address'].lower()
            kwargs = heir_json.copy()
            kwargs['contract'] = contract
            Heir(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().update(details, kwargs)

    def validate(self, details):
        assert('user_address' in details and 'heirs' in details and 'active_to' in details and 'check_interval' in details)
        check.is_address(details['user_address'])
        details['user_address'] = details['user_address'].lower()
        details['active_to'] = datetime.datetime.strptime(details['active_to'], '%Y-%m-%d %H:%M')
        for heir_json in details['heirs']:
            heir_json.get('email', None) and check.is_email(heir_json['email'])
            check.is_address(heir_json['address'])
            heir_json['address'] = heir_json['address'].lower()
            check.is_percent(heir_json['percentage'])
            heir_json['percentage'] = int(heir_json['percentage'])
        check.is_sum_eq_100([h['percentage'] for h in details['heirs']])
        return details


class ContractDetailsLostKeySerializer(ContractDetailsLastwillSerializer):
    class Meta:
        model = ContractDetailsLostKey
        fields = ('user_address', 'active_to', 'check_interval', 'last_check', 'next_check')
        extra_kwargs = {
            'last_check': {'read_only': True},
            'next_check': {'read_only': True},
        }


class ContractDetailsDelayedPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsDelayedPayment
        fields = ('user_address', 'date', 'recepient_address', 'recepient_email')

    def create(self, contract, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().create(kwargs)

    def update(self, contract, details, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().update(details, kwargs)

    def validate(self, details):
        assert('user_address' in details and 'date' in details and 'recepient_address' in details)
        check.is_address(details['user_address'])
        check.is_address(details['recepient_address'])
        details.get('recepient_email', None) and check.is_email(details['recepient_email'])
        return details

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
        return res

class ContractDetailsPizzaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsPizza
        fields = ('user_address', 'pizzeria_address', 'pizza_cost', 'timeout', 'order_id', 'code')
        read_only_fields = ('pizzeria_address', 'timeout', 'code')

    def create(self, contract, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        kwargs['code'] = random.randrange(9999)
        kwargs['salt'] = random.randrange(2**256)
        kwargs['pizza_cost'] = 1 # for testing
        return super().create(kwargs)

    def update(self, contract, details, contract_details):
        kwargs = contract_details_copy()
        kwargs['contract'] = contract
        kwargs['pizza_cost'] = 1 # for testing
        return super().update(details, kwargs)

    def validate(self, details):
        assert('user_address' in details and 'pizza_cost' in details)
        check.is_address(details['user_address'])
        return details

    def to_representation(self, contract_details):
        tes = super().to_representation(contract_details)
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
        return res

class ContractDetailsICOSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsICO
        fields = (
                'soft_cap', 'hard_cap', 'token_name', 'token_short_name', 'is_transferable_at_once',
                'start_date', 'stop_date', 'decimals', 'rate', 'admin_address', 'platform_as_admin',
        )

    def create(self, contract, contract_details):
        token_holders = contract_details.pop('token_holders')
        for th_json in token_holders:
            th_json['address'] = th_json['address'].lower()
            kwargs = th_json.copy()
            kwargs['contract'] = contract
            TokenHolder(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().create(kwargs)

    def update(self, contract, details, contract_details):
        pass

    def validate(self, details):
        assert('admin_address' in details and 'token_holders' in details)
        assert(len(details['token_name']) and len(details['token_short_name']))
        assert(1 <= details['rate'] <= 10**12)
        assert(0 <= details['decimals'] <= 50)
        check.is_address(details['admin_address'])
        assert(details['start_date'] >= datetime.datetime.now().timestamp() + 60*60)
        assert(details['stop_date'] >= details['start_date'] + 60*60)
        assert(details['soft_cap'] >= 0)
        assert(details['hard_cap'] >= details['soft_cap'] + sum([th['amount'] for th in details['token_holders']]))
        for th in details['token_holders']:
            check.is_address(th['address'])
            assert(th['amount'] > 0)
            assert(th['freeze_date'] is None or th['freeze_date'] > details['stop_date'])


    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        token_holder_serializer = TokenHolderSerializer()
        res['token_holders'] = [token_holder_serializer.to_representation(th) for th in contract_details.contract.tokenholder_set.all()]
        res['eth_contract_token'] = EthContractSerializer().to_representation(contract_details.eth_contract_token)
        res['eth_contract_crowdsale'] = EthContractSerializer().to_representation(contract_details.eth_contract_crowdsale)
        res['soft_cap'], res['hard_cap'] = map(int, [res['soft_cap'], res['hard_cap']])
        return res

