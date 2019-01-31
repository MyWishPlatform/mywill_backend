import pyotp
import uuid

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
from lastwill.settings import TRON_URL, MY_WISH_URL
from lastwill.profile.models import SubSite, UserSiteBalance, APIToken


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
    site_name = request.META['HTTP_HOST']
    # print('site name is', site_name)
    if site_name.startswith('cn'):
        site_name = site_name[2:]
    if site_name.startswith('local'):
        print('cut local')
        site_name = site_name[5:]
    if site_name == TRON_URL:
        site_name = MY_WISH_URL
    site = SubSite.objects.get(site_name=site_name)
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


@api_view(http_method_names=['POST'])
def create_api_token(request):
    user = request.user
    if user.is_anonymous:
        raise PermissionDenied()
    token_str = str(uuid.uuid4())
    text = request.data['comment'] if 'comment' in request.data else ''
    APIToken(user=user, token=token_str, comment=text).save()
    return Response({"result": "ok"})


@api_view(http_method_names=['GET'])
def get_api_tokens(request):
    user = request.user
    if user.is_anonymous:
        raise PermissionDenied()
    answer = {"tokens":[]}
    tokens = APIToken.objects.filter(user=user, active=True)
    for token in tokens:
        answer["tokens"].append(token.token)
    return Response(answer)


@api_view(http_method_names=['POST', 'DELETE'])
def delete_api_tokens(request):
    user = request.user
    if user.is_anonymous:
        raise PermissionDenied()
    token_str = request.date['token']
    token = APIToken.objects.get(user=user, token=token_str)
    token.active = False
    token.save()
    return Response({"result": "ok"})
