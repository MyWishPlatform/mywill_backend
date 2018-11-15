import pyotp

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from allauth.account import app_settings
from allauth.account.models import EmailAddress
from allauth.account.views import ConfirmEmailView

from lastwill.contracts.models import Contract
from lastwill.profile.helpers import valid_totp
from lastwill.profile.models import SubSite, UserSiteBalance


class UserConfirmEmailView(ConfirmEmailView):
    def post(self, *args, **kwargs):
        self.object = confirmation = self.get_object()
        confirmation.confirm(self.request)

        '''get_adapter(self.request).add_message(
            self.request,
            messages.SUCCESS,
            'account/messages/email_confirmed.txt',
            {'email': confirmation.email_address.email}
        )'''

        if app_settings.LOGIN_ON_EMAIL_CONFIRMATION:
            resp = self.login_on_confirm(confirmation)
            if resp is not None:
                return resp
        return redirect('/')


@api_view()
def profile_view(request):
    if request.user.is_anonymous:
        raise PermissionDenied()
    site = SubSite.objects.get(site_name=request.META['HTTP_HOST'])
    print(request.user.id, flush=True)
    user_balance = UserSiteBalance.objects.get(subsite=site, user=request.user)
    answer = {
            'username': request.user.email if request.user.email else '{} {}'.format(request.user.first_name, request.user.last_name),
            'contracts': Contract.objects.filter(user=request.user).count(),
            'balance': str(user_balance.balance),
            'internal_address': user_balance.eth_address,
            'internal_btc_address': user_balance.btc_address,
            'use_totp': request.user.profile.use_totp,
            'is_social': request.user.profile.is_social,
            'id': request.user.id,
            'lang': request.user.profile.lang,
            'memo': user_balance.memo,
            'eos_address': 'mywishcoming'
    }
    return Response(answer)


@api_view(http_method_names=['POST'])
def generate_key(request):
    user = request.user
    if user.is_anonymous or user.profile.use_totp:
        raise PermissionDenied()
    user.profile.totp_key = pyotp.random_base32()
    user.profile.save()
    return Response({
            'secret': user.profile.totp_key,
            'issuer': 'mywish.io',
            'user': user.email if user.email else str(user.id),
    })


@api_view(http_method_names=['POST'])
def enable_2fa(request):
    user = request.user
    if user.is_anonymous or not user.profile.totp_key:
        raise PermissionDenied()
    if not valid_totp(user, request.data['totp']):
        raise PermissionDenied()
    user.profile.use_totp = True
    user.profile.save()
    return Response({"result": "ok"})


@api_view(http_method_names=['POST'])
def disable_2fa(request):
    user = request.user
    if user.is_anonymous:
        raise PermissionDenied()
    if not user.profile.use_totp or not valid_totp(user, request.data['totp']):
        raise PermissionDenied()
    user.profile.use_totp = False
    user.profile.save()
    return Response({"result": "ok"})


@api_view(http_method_names=['POST'])
def resend_email(request):
    try:
        em = EmailAddress.objects.get(email=request.data['email'])
    except ObjectDoesNotExist:
        raise PermissionDenied(1)
    if em.verified:
        raise PermissionDenied(2)
    em.send_confirmation(request=request)
    return Response({"result": "ok"})

@api_view(http_method_names=['POST'])
def set_lang(request):
    user = request.user
    if user.is_anonymous:
        raise PermissionDenied()
    user.profile.lang = request.data['lang']
    user.profile.save()
    return Response({"result": "ok"})
