from django.contrib import messages
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from allauth.account import app_settings
from allauth.account.views import ConfirmEmailView
from allauth.account.adapter import get_adapter


class UserConfirmEmailView(ConfirmEmailView):
    """ 
    от базовой вьюхи переопределён редирект
    """
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
    })


