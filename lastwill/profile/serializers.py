import requests
import json
import pyotp
from django.db import transaction
from rest_auth.registration.serializers import RegisterSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from rest_auth.serializers import LoginSerializer, PasswordChangeSerializer, PasswordResetConfirmSerializer
from lastwill.profile.models import Profile
from lastwill.settings import SIGNER
from lastwill.payments.models import BTCAccount


def init_profile(user, is_social=False):
    response = requests.post('http://{}/get_key/'.format(SIGNER)).content
    internal_address = json.loads(response.decode())['addr']
    Profile(user=user, internal_address=internal_address, is_social=is_social).save()
    with transaction.atomic():
        btc_account = BTCAccount.objects.filter(user__isnull=True).first()
        btc_account.user = user
        btc_account.save()


class UserRegisterSerializer(RegisterSerializer):
    def save(self, request):
        user = super().save(request)
        init_profile(user)
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
                if totp != pyotp.TOTP(user.profile.totp_key).now():
                    raise PermissionDenied(1020)
        return res


class PasswordChangeSerializer2FA(PasswordChangeSerializer):
    totp = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        res = super().validate(attrs)
        if self.user.profile.use_totp:
            totp = attrs.get('totp', None)
            if not totp or totp != pyotp.TOTP(self.user.profile.totp_key).now():
                raise PermissionDenied()
        return res


class PasswordResetConfirmSerializer2FA(PasswordResetConfirmSerializer):
    totp = serializers.CharField(required=False, allow_blank=True)
    
    def custom_validation(self, attrs):
        if self.user.profile.use_totp:
            totp = attrs.get('totp', None)
            if not totp:
                raise PermissionDenied(1021)
            print(self.user.email, self.user.id, totp, pyotp.TOTP(self.user.profile.totp_key).now())
            if totp != pyotp.TOTP(self.user.profile.totp_key).now():
                raise PermissionDenied(1022)
