import uuid
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from allauth.account import app_settings
from allauth.account.views import ConfirmEmailView
from allauth.account.adapter import get_adapter
from lastwill.contracts.models import Contract
from lastwill.profile.models import Profile
import pyotp

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
    return Response({
            'username': request.user.username,
            'email': request.user.email,
            'contracts': Contract.objects.filter(user=request.user).count(),
            'is_ghost': not bool(len(request.user.password)),
            'balance': str(request.user.profile.balance),
            'internal_address': request.user.profile.internal_address,
            'internal_btc_address': getattr(request.user.btcaccount_set.first(), 'address', None),
            'use_totp': request.user.profile.use_totp,
    })


@api_view(http_method_names=['POST'])
def create_ghost(request):
    user = User()
    user.username = str(uuid.uuid4())
    user.save()
    Profile(user=user).save()
    login(request, user)
    return Response({
            'username': user.username,
            'email': "",
            'contracts': 0,
            'is_ghost': not bool(len(request.user.password)),
    })


@api_view(http_method_names=['POST'])
def generate_key(request):
    user = request.user
    if user.is_anonymous or not user.email:
        raise PermissionDenied()
    assert(not user.profile.use_totp)
    user.profile.totp_key = pyotp.random_base32()
    user.profile.save()
    return Response({
            'secret': user.profile.totp_key,
            'issuer': 'mywish.io',
            'user': user.email,
    })


@api_view(http_method_names=['POST'])
def enable_2fa(request):
    user = request.user
    if user.is_anonymous or not user.email:
        raise PermissionDenied()
    assert(user.profile.totp_key)
    if pyotp.TOTP(user.profile.totp_key).now() != request.data['totp']:
        raise PermissionDenied()
    user.profile.use_totp = True
    user.profile.save()
    return Response({"result": "ok"})


@api_view(http_method_names=['POST'])
def disable_2fa(request):
    user = request.user
    if user.is_anonymous or not user.email:
        raise PermissionDenied()
    if user.profile.use_totp and pyotp.TOTP(user.profile.totp_key).now() != request.data['totp']:
        raise PermissionDenied()
    user.profile.use_totp = False
    user.profile.save()
    return Response({"result": "ok"})
