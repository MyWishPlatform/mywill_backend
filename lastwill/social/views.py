from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import logout
from django.http import HttpResponse
from django.views import View
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_auth.views import LoginView
from rest_auth.serializers import LoginSerializer
from rest_auth.registration.views import SocialLoginView
from rest_auth.registration.serializers import SocialLoginSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from allauth.account.models import EmailAddress
from lastwill.profile.models import Profile
from lastwill.profile.serializers import init_profile
from lastwill.profile.helpers import valid_totp, valid_metamask_message



class SocialLoginSerializer2FA(SocialLoginSerializer):
    email = serializers.CharField(required=False, allow_blank=True)
    totp = serializers.CharField(required=False, allow_blank=True)


class ProfileAndTotpSocialLoginView(SocialLoginView):
    serializer_class = SocialLoginSerializer2FA

    def login(self):
        self.user = self.serializer.validated_data['user']
        try:
            p = self.user.profile
        except ObjectDoesNotExist:
            self.user.username = str(self.user.id)
            init_profile(self.user, is_social=True, lang=self.serializer.context['request'].COOKIES.get('lang', 'en'))
            self.user.save()
        if self.user.profile.use_totp:
            totp = self.serializer.validated_data.get('totp', None)
            if not totp:
                logout(self.request)
                raise PermissionDenied(1032)
            if not valid_totp(self.user, totp):
                logout(self.request)
                raise PermissionDenied(1033)
        return super().login()


class FacebookLogin(ProfileAndTotpSocialLoginView):
    adapter_class = FacebookOAuth2Adapter


class GoogleLogin(ProfileAndTotpSocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class MetamaskLoginSerializer(LoginSerializer):
    eth_address = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    signed_message = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        address = attrs['address']
        message = attrs['msg']
        signature = attrs['signed_msg']

        if valid_metamask_message(address, message, signature):
            metamask_user = Profile.objects.get(metamask_address=address)
            attrs['user'] = metamask_user
        else:
            raise PermissionDenied(1034)

        return attrs


class MetamaskLogin(LoginView):
    serializer_class = MetamaskLoginSerializer

    def login(self):
        self.user = self.serializer.validated_data['user']
        self.metamask_address = self.serializer.validated_data['address']
        try:
            p = self.user.profile
        except ObjectDoesNotExist:
            self.user.username = str(self.user.id)
            init_profile(self.user, is_social=True, metamask_address=self.metamask_address,
                         lang=self.serializer.context['request'].COOKIES.get('lang', 'en'))
            self.user.save()
        return super.login()


