import requests
import json
from django.db import transaction
from rest_auth.registration.serializers import RegisterSerializer
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
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
