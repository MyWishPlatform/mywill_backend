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

class UserRegisterSerializer(RegisterSerializer):
    def save(self, request):
        response = requests.post('http://{}/get_key/'.format(SIGNER)).content
        internal_address = json.loads(response.decode())['addr']
        print(internal_address, 'internal_address')
#        with transaction.atomic():
#            btc_account = BTCAccount.objects.select_for_update().filter(used=False).first()
#            internal_btc_address = btc_account.address
#            btc_account.used = True
#            btc_account.save()
#        print(internal_btc_address, 'internal_btc_address')
        if request.user.is_anonymous or request.user.password: # anon or normal user
            user = super().save(request)
            user.save()
            profile = Profile(user=user)
            profile.internal_address = internal_address
            profile.save()
        else: # ghost
            user = request.user
            user.username = request.data['username']
            user.email = request.data['email']
            user.set_password(request.data['password1'])
            user.profile.internal_address = internal_address
            user.profile.save()
            user.save()
            setup_user_email(request, request.user, [])
        with transaction.atomic():
            btc_account = BTCAccount.objects.filter(user__isnull=True).first()
            btc_account.user = user
            btc_account.save()
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
