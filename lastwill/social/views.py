from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import logout
from django.http import HttpResponse
from django.views import View
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_auth.registration.views import SocialLoginView
from rest_auth.registration.serializers import SocialLoginSerializer
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from allauth.account.models import EmailAddress
import pyotp
from lastwill.profile.models import Profile
from lastwill.profile.serializers import init_profile

class SocialLoginSerializer2FA(SocialLoginSerializer):
    email = serializers.CharField(required=False, allow_blank=True)
    totp = serializers.CharField(required=False, allow_blank=True)


class ProfileAndTotpSocialLoginView(SocialLoginView):
    serializer_class = SocialLoginSerializer2FA

    '''
    def process_login(self):
#        Profile.objects.get_or_create(user=self.user, is_social=True)
        # social users will not receive emails.


        if not len(self.user.emailaddress_set.all()):
            email = self.serializer.validated_data.get('email', None)
            if not email:
                raise PermissionDenied(1030)
            print('will send confirmation')
            em = EmailAddress(user=self.user, email=email)
            em.save()
            em.send_confirmation() # signup ?
            return Response({})
        if not self.user.emailaddress_set.all()[0].verified:
            raise PermissionDenied(1031)


#        if not self.user.profile:
        try:
            p = self.user.profile
        except ObjectDoesNotExist:
            self.user.username = str(self.user.id)
            init_profile(self.user, is_social=True)
            self.user.save()
        if self.user.profile.use_totp:
            totp = self.serializer.validated_data.get('totp', None)
            if not totp:
                logout(self.request)
                raise PermissionDenied(1032)
            if totp != pyotp.TOTP(self.user.profile.totp_key).now():
                logout(self.request)
                raise PermissionDenied(1033)
        return super().process_login()
    '''
    def login(self):
        self.user = self.serializer.validated_data['user']
        try:
            p = self.user.profile
        except ObjectDoesNotExist:
            self.user.username = str(self.user.id)
            init_profile(self.user, is_social=True)
            self.user.save()
        if self.user.profile.use_totp:
            totp = self.serializer.validated_data.get('totp', None)
            if not totp:
                logout(self.request)
                raise PermissionDenied(1032)
            if totp != pyotp.TOTP(self.user.profile.totp_key).now():
                logout(self.request)
                raise PermissionDenied(1033)
        return super().login()
        

class FacebookLogin(ProfileAndTotpSocialLoginView):
    adapter_class = FacebookOAuth2Adapter

class GoogleLogin(ProfileAndTotpSocialLoginView):
    adapter_class = GoogleOAuth2Adapter

class MyView(View):

    def get(self, request):
        return HttpResponse('OK!')
