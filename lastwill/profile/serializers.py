import requests
import json
from rest_auth.registration.serializers import RegisterSerializer
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from lastwill.profile.models import Profile
from lastwill.settings import SIGNER

class UserRegisterSerializer(RegisterSerializer):
    def save(self, request):
        response = requests.post('http://{}/get_key/'.format(SIGNER)).content
        internal_address = json.loads(response.decode())['addr']
        print(internal_address, 'internal_address')
        if request.user.is_anonymous or request.user.password: # anon or normal user
            res = super().save(request)
            res.save()
            profile = Profile(user=res)
            profile.internal_address = internal_address
            profile.save()
            return res
        else: # ghost
            request.user.username = request.data['username']
            request.user.email = request.data['email']
            request.user.set_password(request.data['password1'])
            request.user.profile.internal_address = internal_address
            request.user.profile.save()
            request.user.save()
            setup_user_email(request, request.user, [])
            return request.user

