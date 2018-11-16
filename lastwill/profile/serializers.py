import requests
import os
import hashlib
import binascii

from bip32utils import BIP32Key
from eth_keys import keys

from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from rest_auth.registration.serializers import RegisterSerializer
from rest_auth.serializers import (
    LoginSerializer, PasswordChangeSerializer, PasswordResetConfirmSerializer
)

from lastwill.profile.models import Profile, UserSiteBalance, SubSite
from lastwill.settings import ROOT_PUBLIC_KEY, ROOT_PUBLIC_KEY_EOSISH, BITCOIN_URLS, MY_WISH_URL, EOSISH_URL
from lastwill.profile.helpers import valid_totp

def init_profile(user, is_social=False, lang='en'):
    m = hashlib.sha256()
    memo_str1 = os.urandom(8)
    memo_str2 = os.urandom(8)
    m.update(memo_str1)
    memo_str1 = binascii.hexlify(memo_str1 + m.digest()[0:2])
    m.update(memo_str2)
    memo_str2 = binascii.hexlify(memo_str2 + m.digest()[0:2])

    wish_key = BIP32Key.fromExtendedKey(ROOT_PUBLIC_KEY, public=True)
    eosish_key = BIP32Key.fromExtendedKey(ROOT_PUBLIC_KEY_EOSISH, public=True)

    btc_address1 = wish_key.ChildKey(user.id).Address()
    btc_address2 = eosish_key.ChildKey(user.id).Address()
    eth_address1 = keys.PublicKey(wish_key.ChildKey(user.id).K.to_string()).to_checksum_address().lower()
    eth_address2 = keys.PublicKey(eosish_key.ChildKey(user.id).K.to_string()).to_checksum_address().lower()

    wish = SubSite.objects.get(site_name=MY_WISH_URL)
    eosish = SubSite.objects.get(site_name=EOSISH_URL)

    Profile(user=user, is_social=is_social, lang=lang).save()
    UserSiteBalance(
        user=user, subsite=wish,
        eth_address=eth_address1,
        btc_address=btc_address1,
        memo=memo_str1
    ).save()
    UserSiteBalance(
        user=user, subsite=eosish,
        eth_address=eth_address2,
        btc_address=btc_address2,
        memo=memo_str2
    ).save()
    requests.post(
        BITCOIN_URLS['main'],
        json={
            'method': 'importaddress',
            'params': [btc_address1, btc_address1, False],
            'id': 1, 'jsonrpc': '1.0'
        }
    )
    requests.post(
        BITCOIN_URLS['main'],
        json={
            'method': 'importaddress',
            'params': [btc_address2, btc_address2, False],
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
