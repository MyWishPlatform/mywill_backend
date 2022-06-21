from django.contrib import admin

from .models import (
    Profile, SubSite,
    UserSiteBalance, APIToken
)


# profile
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    search_fields = ['id', 'user__username', 'user__id', 'user__email']
    list_display = '__str__', 'lang', 'balance', 'eos_balance', 'totp_key', 'last_used_totp'


@admin.register(SubSite)
class SubSiteAdmin(admin.ModelAdmin):
    list_display = '__str__', 'currencies'


@admin.register(UserSiteBalance)
class UserSiteBalanceAdmin(admin.ModelAdmin):
    search_fields = ['id', 'user__username', 'user__id', 'user__email']
    list_display = '__str__', 'balance'


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    search_fields = ['id', 'user__username', 'user__id', 'user__email']
    list_display = '__str__', 'last_accessed', 'active'
