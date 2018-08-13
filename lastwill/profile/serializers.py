import requests
import string
import random

from bip32utils import BIP32Key
from bip32utils import BIP32_HARDEN
from eth_keys import keys

from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from rest_auth.registration.serializers import RegisterSerializer
from rest_auth.serializers import (
    LoginSerializer, PasswordChangeSerializer, PasswordResetConfirmSerializer
)

from lastwill.profile.models import Profile
from lastwill.settings import ROOT_PUBLIC_KEY, BITCOIN_URLS
from lastwill.payments.models import BTCAccount
from lastwill.profile.helpers import valid_totp

def init_profile(user, is_social=False, lang='en'):

    key = BIP32Key.fromExtendedKey(ROOT_PUBLIC_KEY, public=True)
    btc_address = key.ChildKey(user.id).Address()
    chars = string.ascii_lowercase + string.digits
    memo_str = ''.join(random.choice(chars) for _ in range(16))

    btc_account = BTCAccount(address=btc_address)
    btc_account.user = user
    btc_account.save()
    eth_address = keys.PublicKey(key.ChildKey(user.id).K.to_string()).to_checksum_address()
    Profile(
        user=user, internal_address=eth_address,
        is_social=is_social, lang=lang, memo=memo_str
    ).save()
    requests.post(
        BITCOIN_URLS['main'],
        json={
            'method': 'importaddress',
            'params': [btc_address, btc_address, False],
            'id': 1, 'jsonrpc': '1.0'
        }
    )


class UserRegisterSerializer(RegisterSerializer):
    def save(self, request):
        user = super().save(request)
        init_profile(user, lang=request.COOKIES.get('lang', 'en'))
        return user


class UserLoginSerializer2FA(LoginSerializer):
    totp = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        res = super().validate(attrs)
        if attrs['user']:
            user = attrs['user']
            if user.profile.use_totp:
                totp = attrs.get('totp', None)
                if not totp:
                    raise PermissionDenied(1019)
                if not valid_totp(user, totp):
                    raise PermissionDenied(1020)
        return res


class PasswordChangeSerializer2FA(PasswordChangeSerializer):
    totp = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        res = super().validate(attrs)
        if self.user.profile.use_totp:
            totp = attrs.get('totp', None)
            if totp is None or not valid_totp(self.user, totp):
                raise PermissionDenied()
        return res


class PasswordResetConfirmSerializer2FA(PasswordResetConfirmSerializer):
    totp = serializers.CharField(required=False, allow_blank=True)
    
    def custom_validation(self, attrs):
        if self.user.profile.use_totp:
            totp = attrs.get('totp', None)
            if not totp:
                raise PermissionDenied(1021)
            if not valid_totp(self.user, totp):
                raise PermissionDenied(1022)
