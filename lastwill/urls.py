"""lastwill URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from allauth.account.views import confirm_email as allauthemailconfirmation
from rest_framework.routers import DefaultRouter

from lastwill.main.views import index, balance, login, eth2rub, exc_rate, count_tokens_of_ICOcontract
from lastwill.profile.views import UserConfirmEmailView, profile_view, generate_key, enable_2fa, disable_2fa
from lastwill.contracts.api import ContractViewSet, get_cost, get_code, test_comp, get_contract_types, pizza_delivered, deploy, get_token_contracts
from lastwill.other.api import SentenceViewSet
from lastwill.social.views import FacebookLogin, GoogleLogin, MyView

router = DefaultRouter(trailing_slash=True)
router.register(r'contracts', ContractViewSet)
router.register(r'sentences', SentenceViewSet)

urlpatterns = [
    url(r'^reset', index),
    url(r'^', include('django.contrib.auth.urls')),
    url(r'^jopa/', admin.site.urls),
    url(r'^api/', include(router.urls)),
    url(
            r'^api/rest-auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$',
            allauthemailconfirmation, name="account_confirm_email"
    ),
    url(r'^api/rest-auth/', include('rest_auth.urls')),
    url(r'^api/rest-auth/registration/', include('rest_auth.registration.urls')),
    url(r'^/email-verification-sent/$', index, name='account_email_verification_sent'),
    url(r'^api/profile/', profile_view),
    url(r'^api/get_cost/', get_cost),
    url(r'^api/balance/', balance),
    url(r'^auth/', login),
    url(r'^api/get_code/', get_code),
    url(r'^api/test_comp/', test_comp),
#    url(r'^api/create_ghost/', create_ghost),
    url(r'^api/get_contract_types', get_contract_types),
    url(r'^api/eth2rub/', eth2rub),
    url(r'^api/exc_rate/', exc_rate),
    url(r'^api/pizza_delivered/', pizza_delivered),
    url(r'^api/deploy/', deploy),
    url(r'^api/get_token_contracts/', get_token_contracts),
    url(r'^api/generate_key/', generate_key),
    url(r'^api/enable_2fa/', enable_2fa),
    url(r'^api/disable_2fa/', disable_2fa),
    url(r'^api/rest-auth/facebook/$', FacebookLogin.as_view(), name='fb_login'),
    url(r'^api/rest-auth/google/$', GoogleLogin.as_view(), name='google_login'),
    url(r'^/$', index, name='socialaccount_signup'),
    url(r'^test/$', MyView.as_view(), name='test'),
    url(r'^/count_tokens_in_ICO/', count_tokens_of_ICOcontract, name='count_ICOtokens'),
]

urlpatterns += url(r'^/*', index, name='all'),

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
