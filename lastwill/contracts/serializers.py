import datetime
import binascii
from ethereum.abi import method_id as m_id
from rlp.utils import int_to_big_endian

from django.db import transaction
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

import lastwill.check as check
from lastwill.settings import DEFAULT_FROM_EMAIL, test_logger
from lastwill.parint import ParInt
from lastwill.contracts.models import (
        Contract, Heir, EthContract, TokenHolder, WhitelistAddress,
        NeoContract, ContractDetailsNeoICO, ContractDetailsNeo,
        ContractDetailsToken, ContractDetailsICO,
        ContractDetailsAirdrop, AirdropAddress,
        ContractDetailsLastwill, ContractDetailsLostKey,
        ContractDetailsDelayedPayment, ContractDetailsInvestmentPool,
        InvestAddress
)
from exchange_API import to_wish, convert
from lastwill.consts import MAIL_NETWORK
import email_messages
from neocore.Cryptography.Crypto import Crypto
from neocore.UInt160 import UInt160


def count_sold_tokens(address):
    contract = EthContract.objects.get(address=address).contract

    par_int = ParInt()

    method_sign = '0x' + binascii.hexlify(
        int_to_big_endian(m_id('totalSupply', []))).decode()
    sold_tokens = par_int.eth_call({'to': address,
                                    'data': method_sign,
    })
    sold_tokens = '0x0' if sold_tokens == '0x' else sold_tokens
    sold_tokens = int(sold_tokens, 16) / 10**contract.get_details().decimals
    return sold_tokens


class HeirSerializer(serializers.ModelSerializer):
    class Meta:
        model = Heir
        fields = ('address', 'email', 'percentage')


class TokenHolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenHolder
        fields = ('address', 'amount', 'freeze_date', 'name')


class ContractSerializer(serializers.ModelSerializer):
    contract_details = serializers.JSONField(write_only=True)

    class Meta:
        model = Contract
        fields = (
            'id', 'user', 'owner_address', 'state', 'created_date', 'balance',
            'cost', 'name', 'contract_type', 'contract_details', 'network',
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

        contract_type = validated_data['contract_type']
        details_serializer = self.get_details_serializer(
            contract_type
        )(context=self.context)
        contract_details = validated_data.pop('contract_details')
        details_serializer.validate(contract_details)
        validated_data['cost'] = Contract.get_details_model(
            contract_type
        ).calc_cost(contract_details, validated_data['network'])
        transaction.set_autocommit(False)
        try:
            contract = super().create(validated_data)
            details_serializer.create(contract, contract_details)
        except:
            transaction.rollback()
            test_logger.error('Contract Serializer create except')
            raise
        else:
            transaction.commit()
        finally:
            transaction.set_autocommit(True)
        if validated_data['user'].email:
            network_name = ''
            network = validated_data['network']
            if network.name == 'ETHEREUM_MAINNET':
                network_name = 'Ethereum'
            if network.name == 'ETHEREUM_ROPSTEN':
                network_name = 'Ropsten (Ethereum Testnet)'
            if network.name == 'RSK_MAINNET':
                network_name = 'RSK'
            if network.name == 'RSK_TESTNET':
                network_name = 'RSK Testnet'
            if network.name == 'NEO_MAINNET':
                network_name = 'NEO'
            if network.name == 'NEO_TESTNET':
                network_name = 'NEO Testnet'

            send_mail(
                    email_messages.create_subject,
                    email_messages.create_message.format(
                        network_name=network_name
                    ),
                    DEFAULT_FROM_EMAIL,
                    [validated_data['user'].email]
            )
        return contract

    def to_representation(self, contract):
        res = super().to_representation(contract)
        res['contract_details'] = self.get_details_serializer(
            contract.contract_type
        )(context=self.context).to_representation(contract.get_details())
        if contract.state != 'CREATED':
            eth_cost = res['cost']
        else:
            eth_cost = Contract.get_details_model(
                contract.contract_type
            ).calc_cost(res['contract_details'], contract.network)
        res['cost'] = {
            'ETH': str(eth_cost),
            'WISH': str(int(to_wish('ETH', int(eth_cost)))),
            'BTC': str(int(eth_cost) * convert('ETH', 'BTC')['BTC'])
        }
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
            details_serializer = self.get_details_serializer(
                contract_type
            )(context=self.context)
            details_serializer.validate(contract_details)
            validated_data['cost'] = contract.get_details_model(
                contract_type
            ).calc_cost(contract_details, validated_data['network'])
            details_serializer.update(
                contract, contract.get_details(), contract_details
            )

        return super().update(contract, validated_data)

    def get_details_serializer(self, contract_type):
        return {
            0: ContractDetailsLastwillSerializer,
            1: ContractDetailsLostKeySerializer,
            2: ContractDetailsDelayedPaymentSerializer,
            4: ContractDetailsICOSerializer,
            5: ContractDetailsTokenSerializer,
            6: ContractDetailsNeoSerializer,
            7: ContractDetailsNeoICOSerializer,
            8: ContractDetailsAirdropSerializer,
            9: ContractDetailsInvestmentPoolSerializer
        }[contract_type]


class EthContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = EthContract
        fields = (
            'id', 'address', 'source_code', 'abi',
            'bytecode', 'compiler_version', 'constructor_arguments'
        )


class WhitelistAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhitelistAddress
        fields = ('address',)


class ContractDetailsLastwillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsLastwill
        fields = (
            'user_address', 'active_to', 'check_interval',
            'last_check', 'next_check', 'email', 'platform_alive',
            'platform_cancel', 'last_reset', 'last_press_imalive'
        )
        extra_kwargs = {
            'last_check': {'read_only': True},
            'next_check': {'read_only': True},
            'last_reset': {'read_only': True},
            'last_press_imalive': {'read_only': True}
        }

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        heir_serializer = HeirSerializer()
        if not contract_details:
           print('*'*50, contract_details.id, flush=True)
        res['heirs'] = [heir_serializer.to_representation(heir) for heir in contract_details.contract.heir_set.all()]
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)

        if contract_details.contract.network.name in ['RSK_MAINNET', 'RSK_TESTNET']:
            btc_key = contract_details.btc_key
            if btc_key:
                res['btc_address'] = contract_details.btc_key.btc_address
        if contract_details.contract.network.name in ['ETHEREUM_ROPSTEN', 'RSK_TESTNET']:
            res['eth_contract']['source_code'] = ''
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
        if 'user_address' not in details or 'heirs' not in details:
            raise ValidationError
        if 'active_to' not in details or 'check_interval' not in details:
            raise ValidationError
        if details['check_interval'] > 315360000:
            raise ValidationError
        check.is_address(details['user_address'])
        details['user_address'] = details['user_address'].lower()
        details['active_to'] = datetime.datetime.strptime(
            details['active_to'], '%Y-%m-%d %H:%M'
        )
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
        fields = (
            'user_address',
            'active_to',
            'check_interval',
            'last_check',
            'next_check'
        )
        extra_kwargs = {
            'last_check': {'read_only': True},
            'next_check': {'read_only': True},
        }


class ContractDetailsDelayedPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsDelayedPayment
        fields = (
            'user_address', 'date', 'recepient_address', 'recepient_email'
        )

    def create(self, contract, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().create(kwargs)

    def update(self, contract, details, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().update(details, kwargs)

    def validate(self, details):
        if 'user_address' not in details or 'date' not in details or 'recepient_address' not in details:
            raise ValidationError
        check.is_address(details['user_address'])
        check.is_address(details['recepient_address'])
        details.get('recepient_email', None) and check.is_email(details['recepient_email'])
        return details

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
        if contract_details.contract.network.name in ['ETHEREUM_ROPSTEN', 'RSK_TESTNET']:
            res['eth_contract']['source_code'] = ''
        return res


class ContractDetailsICOSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsICO
        fields = (
                'soft_cap', 'hard_cap', 'token_name', 'token_short_name',
                'is_transferable_at_once','start_date', 'stop_date',
                'decimals', 'rate', 'admin_address', 'platform_as_admin',
                'time_bonuses', 'amount_bonuses', 'continue_minting',
                'cold_wallet_address', 'reused_token',
                'token_type', 'min_wei', 'max_wei', 'allow_change_dates',
                'whitelist'
        )

    def create(self, contract, contract_details):
        token_id = contract_details.pop('token_id', None)
        token_holders = contract_details.pop('token_holders')
        for th_json in token_holders:
            th_json['address'] = th_json['address'].lower()
            kwargs = th_json.copy()
            kwargs['contract'] = contract
            TokenHolder(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        res = super().create(kwargs)
        if token_id:
            res.eth_contract_token_id = token_id
            res.save()
        return res

    def validate(self, details):
        now = timezone.now().timestamp() + 600
        if 'eth_contract_token' in details and 'id' in details['eth_contract_token'] and details['eth_contract_token']['id']:
            token_model = EthContract.objects.get(id=details['eth_contract_token']['id'])
            token_details = token_model.contract.get_details()
            details.pop('eth_contract_token')
            details['token_name'] = token_details.token_name
            details['token_short_name'] = token_details.token_short_name
            details['decimals'] = token_details.decimals
            details['reused_token'] = True
            details['token_id'] = token_model.id
            details['token_type'] = token_details.token_type
        else:
            if '"' in details['token_name'] or '\n' in details['token_name']:
                raise ValidationError
            if '"' in details['token_short_name'] or '\n' in details['token_short_name']:
                raise ValidationError
            if details['decimals'] < 0 or details['decimals'] > 50:
                raise ValidationError
            details['reused_token'] = False
            if details.get('token_type', 'ERC20') not in ('ERC20, ERC223'):
                raise ValidationError
        for k in ('hard_cap', 'soft_cap'):
            details[k] = int(details[k])
        for k in ('max_wei', 'min_wei'):
            details[k] = (int(details[k]) if details.get(k, None) else None)
        if details['min_wei'] is not None and details['max_wei'] is not None and details['min_wei'] > details['max_wei']:
            raise ValidationError
        if details['max_wei'] is not None and details['max_wei'] < 10*10**18:
            raise ValidationError
        if 'admin_address' not in details or 'token_holders' not in details:
            raise ValidationError
        if len(details['token_holders']) > 5:
            raise ValidationError
        for th in details['token_holders']:
            th['amount'] = int(th['amount'])
        if not len(details['token_name']) or not len(details['token_short_name']):
            raise ValidationError
        if details['rate'] < 1 or details['rate'] > 10**12:
            raise ValidationError
        check.is_address(details['admin_address'])
        if details['start_date'] < datetime.datetime.now().timestamp() + 5*60:
            raise ValidationError({'result': 1}, code=400)
        if details['stop_date'] < details['start_date'] + 5*60:
            raise ValidationError
        if details['hard_cap'] < details['soft_cap']:
            raise ValidationError
        if details['soft_cap'] < 0:
            raise ValidationError
        for th in details['token_holders']:
            check.is_address(th['address'])
            if th['amount'] < 0:
                raise ValidationError
            if th['freeze_date'] is not None and th['freeze_date'] < now:
                test_logger.error('Error freeze date in ICO serializer')
                raise ValidationError({'result': 2}, code=400)
        amount_bonuses = details['amount_bonuses']
        min_amount = 0
        for bonus in amount_bonuses:
            if bonus.get('min_amount', None) is not None:
                if bonus.get('max_amount', None) is None:
                    raise ValidationError
                if int(bonus['min_amount']) < min_amount:
                    raise ValidationError
                min_amount = int(bonus['max_amount'])
            if int(bonus['min_amount']) >= int(bonus['max_amount']):
                raise ValidationError
            if bonus['bonus'] < 0.1:
                raise ValidationError
        time_bonuses = details['time_bonuses']
        for bonus in time_bonuses:
            if bonus.get('min_amount', None) is not None:
                if bonus.get('max_amount', None) is None:
                    raise ValidationError
                if not (0 <= int(bonus['min_amount']) < int(bonus['max_amount']) <= int(details['hard_cap'])):
                    raise ValidationError
            if bonus.get('min_time', None) is not None:
                if bonus.get('max_time', None) is None:
                    raise ValidationError
                if not (int(details['start_date']) <= int(bonus['min_time']) < int(bonus['max_time']) <= int(details['stop_date'])):
                    raise ValidationError
            if bonus['bonus'] < 0.1:
                raise ValidationError

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        token_holder_serializer = TokenHolderSerializer()
        res['token_holders'] = [token_holder_serializer.to_representation(th) for th in contract_details.contract.tokenholder_set.order_by('id').all()]
        res['eth_contract_token'] = EthContractSerializer().to_representation(contract_details.eth_contract_token)
        res['eth_contract_crowdsale'] = EthContractSerializer().to_representation(contract_details.eth_contract_crowdsale)
        res['rate'] = int(res['rate'])
        if contract_details.contract.network.name in ['ETHEREUM_ROPSTEN', 'RSK_TESTNET']:
            res['eth_contract_token']['source_code'] = ''
            res['eth_contract_crowdsale']['source_code'] = ''
        return res

    def update(self, contract, details, contract_details): 
        token_id = contract_details.pop('token_id', None)
        contract.tokenholder_set.all().delete()
        token_holders = contract_details.pop('token_holders')
        for th_json in token_holders:
            th_json['address'] = th_json['address'].lower()
            kwargs = th_json.copy()
            kwargs['contract'] = contract
            TokenHolder(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        kwargs.pop('eth_contract_token', None)
        kwargs.pop('eth_contract_crowdsale', None)

        if token_id:
            details.eth_contract_token_id = token_id
        return super().update(details, kwargs)


class ContractDetailsTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsToken
        fields = (
                'token_name', 'token_short_name', 'decimals',
                'admin_address', 'token_type', 'future_minting',
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
          
    def validate(self, details):
        now = timezone.now().timestamp() + 600
        if '"' in details['token_name'] or '\n' in details['token_name']:
            raise ValidationError
        if '"' in details['token_short_name'] or '\n' in details['token_short_name']:
            raise ValidationError
        if not (0 <= details['decimals'] <= 50):
            raise ValidationError
        for th in details['token_holders']:
            th['amount'] = int(th['amount'])
        if 'admin_address' not in details or 'token_holders' not in details:
            raise ValidationError
        if details['token_name'] == '' or details['token_short_name'] == '':
            raise ValidationError
        check.is_address(details['admin_address'])
        for th in details['token_holders']:
            check.is_address(th['address'])
            if th['amount'] <= 0:
                raise ValidationError
            if th['freeze_date'] is not None and th['freeze_date'] < now:
                test_logger.error('Error freeze date in token serializer')
                raise ValidationError({'result': 2}, code=400)

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        token_holder_serializer = TokenHolderSerializer()
        res['token_holders'] = [token_holder_serializer.to_representation(th) for th in contract_details.contract.tokenholder_set.order_by('id').all()]
        res['eth_contract_token'] = EthContractSerializer().to_representation(contract_details.eth_contract_token)
        if contract_details.eth_contract_token and contract_details.eth_contract_token.ico_details_token.filter(contract__state='ACTIVE'):
            res['crowdsale'] = contract_details.eth_contract_token.ico_details_token.filter(contract__state__in=('ACTIVE','ENDED')).order_by('id')[0].contract.id
        if contract_details.contract.network.name in ['ETHEREUM_ROPSTEN', 'RSK_TESTNET']:
            res['eth_contract_token']['source_code'] = ''
        return res

    def update(self, contract, details, contract_details):
        contract.tokenholder_set.all().delete()
        token_holders = contract_details.pop('token_holders')
        for th_json in token_holders:
            th_json['address'] = th_json['address'].lower()
            kwargs = th_json.copy()
            kwargs['contract'] = contract
            TokenHolder(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        kwargs.pop('eth_contract_token', None)
        return super().update(details, kwargs)


class NeoContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = NeoContract
        fields = ('id', 'address')


class ContractDetailsNeoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsNeo
        fields = (
            'token_name', 'decimals', 'token_short_name', 'admin_address', 'future_minting',
        )

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        res['neo_contract_token'] = NeoContractSerializer().to_representation(contract_details.neo_contract)
        if res['neo_contract_token']['address']:
            res['neo_contract_token']['script_hash'] = res['neo_contract_token']['address']
            res['neo_contract_token']['address'] = Crypto.ToAddress(UInt160.ParseString(res['neo_contract_token']['address']))
        token_holder_serializer = TokenHolderSerializer()
        res['token_holders'] = [
            token_holder_serializer.to_representation(th)
            for th in
            contract_details.contract.tokenholder_set.order_by(
                        'id').all()
        ]
        if not contract_details:
           print('*'*50, contract_details.id, flush=True)
        # res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
        return res

    def create(self, contract, contract_details):
        token_holders = contract_details.pop('token_holders')
        for th_json in token_holders:
            th_json['address'] = th_json['address']
            kwargs = th_json.copy()
            kwargs['contract'] = contract
            TokenHolder(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().create(kwargs)
    
    def update(self, contract, details, contract_details):
        contract.tokenholder_set.all().delete()
        token_holders = contract_details.pop('token_holders')
        for th_json in token_holders:
            th_json['address'] = th_json['address']
            kwargs = th_json.copy()
            kwargs['contract'] = contract
            TokenHolder(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().update(details, kwargs)

    def validate(self, details):
        if details['decimals'] < 0 or details['decimals'] > 9:
            raise ValidationError
        if len(details['token_short_name']) == 0 or len(details['token_short_name']) > 9:
            raise ValidationError


class ContractDetailsNeoICOSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsNeoICO
        fields = (
                'hard_cap', 'token_name', 'token_short_name',
                'start_date', 'stop_date', 'decimals', 'rate',
                'admin_address'
        )

    def create(self, contract, contract_details):
        token_id = contract_details.pop('token_id', None)
        token_holders = contract_details.pop('token_holders')
        for th_json in token_holders:
            th_json['address'] = th_json['address']
            kwargs = th_json.copy()
            kwargs['contract'] = contract
            TokenHolder(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        res = super().create(kwargs)
        if token_id:
            res.neo_contract_crowdsale_id = token_id
            res.save()
        return res

    def validate(self, details):
        if '"' in details['token_name'] or '\n' in details['token_name']:
            raise ValidationError
        if '"' in details['token_short_name'] or '\n' in details['token_short_name']:
            raise ValidationError
        if details['decimals'] < 0 or details['decimals'] > 9:
            raise ValidationError
        if 'admin_address' not in details:
            raise ValidationError
        if len(details['token_name']) == '' or len(details['token_short_name']) == '':
            raise ValidationError
        if not (1 <= details['rate'] <= 10**12):
            raise ValidationError
        if details['start_date'] < datetime.datetime.now().timestamp() + 5*60:
            raise ValidationError({'result': 1}, code=400)
        if details['stop_date'] < details['start_date'] + 5*60:
            raise ValidationError
        details['hard_cap'] = int(details['hard_cap'])
        if details['hard_cap'] < 10:
            raise ValidationError

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        token_holder_serializer = TokenHolderSerializer()
        res['token_holders'] = [
            token_holder_serializer.to_representation(th) for th in contract_details.contract.tokenholder_set.order_by('id').all()
        ]
        res['neo_contract_crowdsale'] = NeoContractSerializer().to_representation(contract_details.neo_contract_crowdsale)
        if res['neo_contract_crowdsale']['address']:
            res['neo_contract_crowdsale']['script_hash'] = res['neo_contract_crowdsale']['address']
            res['neo_contract_crowdsale']['address'] = Crypto.ToAddress(UInt160.ParseString(res['neo_contract_crowdsale']['address']))

        res['rate'] = int(res['rate'])
        if contract_details.contract.network.name in ['ETHEREUM_ROPSTEN', 'RSK_TESTNET']:
            res['neo_contract_crowdsale']['source_code'] = ''
        return res

    def update(self, contract, details, contract_details):
        token_id = contract_details.pop('token_id', None)
        contract.tokenholder_set.all().delete()
        token_holders = contract_details.pop('token_holders')
        for th_json in token_holders:
            th_json['address'] = th_json['address']
            kwargs = th_json.copy()
            kwargs['contract'] = contract
            TokenHolder(**kwargs).save()
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        kwargs.pop('neo_contract_crowdsale', None)

        if token_id:
            details.neo_contract_crowdsale_id = token_id
        return super().update(details, kwargs)


class ContractDetailsAirdropSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsAirdrop
        fields = ('admin_address', 'token_address')

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
        res['added_count'] = contract_details.contract.airdropaddress_set.filter(state='added', active=True).count()
        res['processing_count'] = contract_details.contract.airdropaddress_set.filter(state='processing', active=True).count()
        res['sent_count'] = contract_details.contract.airdropaddress_set.filter(state='sent', active=True).count()
        return res

    def create(self, contract, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().create(kwargs)

    def update(self, contract, details, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().update(details, kwargs)


class AirdropAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirdropAddress
        fields = ('address', 'amount', 'state')


class InvestAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestAddress
        fields = ('address', 'amount')


class ContractDetailsInvestmentPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractDetailsInvestmentPool
        fields = (
                'soft_cap', 'hard_cap', 'start_date', 'stop_date',
                'admin_address', 'admin_percent', 'ico_address',
                'min_wei', 'max_wei', 'allow_change_dates', 'whitelist',
                'investment', 'investment_address', 'send_tokens_hard_cap',
                'send_tokens_soft_cap'
        )

    def create(self, contract, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        res = super().create(kwargs)
        return res

    def validate(self, details):
        for k in ('hard_cap', 'soft_cap'):
            details[k] = int(details[k])
        for k in ('max_wei', 'min_wei'):
            details[k] = (int(details[k]) if details.get(k, None) else None)
        if details['min_wei'] is not None and details['max_wei'] is not None and details['min_wei'] > details['max_wei']:
            raise ValidationError
        if details['max_wei'] is not None and details['max_wei'] < 10*10**18:
            raise ValidationError
        if 'user_address' not in details or 'admin_percent' not in details:
            raise ValidationError
        check.is_address(details['user_address'])
        if details['start_date'] < datetime.datetime.now().timestamp() + 5*60:
            raise ValidationError({'result': 1}, code=400)
        if details['stop_date'] < details['start_date'] + 5*60:
            raise ValidationError
        if details['hard_cap'] < details['soft_cap']:
            raise ValidationError
        if details['soft_cap'] < 0:
            raise ValidationError

    def to_representation(self, contract_details):
        res = super().to_representation(contract_details)
        invest_address_serializer = InvestAddressSerializer()
        res['investment_addresses'] = [invest_address_serializer.to_representation(th) for th in contract_details.contract.investaddress_set.order_by('id').all()]
        res['eth_contract'] = EthContractSerializer().to_representation(contract_details.eth_contract)
        if contract_details.contract.network.name in ['ETHEREUM_ROPSTEN', 'RSK_TESTNET']:
            res['eth_contract']['source_code'] = ''
        return res

    def update(self, contract, details, contract_details):
        kwargs = contract_details.copy()
        kwargs['contract'] = contract
        return super().update(details, kwargs)
