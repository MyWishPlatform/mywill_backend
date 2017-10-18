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
from allauth.account.views import confirm_email as allauthemailconfirmation
from rest_framework.routers import DefaultRouter

from lastwill.main.views import index, balance, login
from lastwill.profile.views import UserConfirmEmailView, profile_view, create_ghost
from lastwill.contracts.api import ContractViewSet, get_cost, get_code, test_comp, get_contract_types


router = DefaultRouter(trailing_slash=True)
router.register(r'contracts', ContractViewSet)

urlpatterns = [
    url(r'^reset', index),
    url(r'^', include('django.contrib.auth.urls')),
    url(r'^admin/', admin.site.urls),
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
    url(r'^api/create_ghost/', create_ghost),
    url(r'^api/get_contract_types', get_contract_types),
]

urlpatterns += url(r'^/*', index, name='all'),

