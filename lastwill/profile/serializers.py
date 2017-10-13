from rest_auth.registration.serializers import RegisterSerializer
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email

class UserRegisterSerializer(RegisterSerializer):
    def save(self, request):
        if request.user.is_anonymous or request.user.password: # anon or normal user
            return super().save(request)
        else: # ghost
            request.user.username = request.data['username']
            request.user.email = request.data['email']
            request.user.set_password(request.data['password1'])
            request.user.save()
            setup_user_email(request, request.user, [])
            return request.user

