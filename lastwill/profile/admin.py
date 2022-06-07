from django.contrib import admin

from .models import APIToken, Profile, SubSite, UserSiteBalance


# profile
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = '__str__', 'lang', 'balance', 'eos_balance', 'totp_key', 'last_used_totp'


@admin.register(SubSite)
class SubSiteAdmin(admin.ModelAdmin):
    list_display = '__str__', 'currencies'


@admin.register(UserSiteBalance)
class UserSiteBalanceAdmin(admin.ModelAdmin):
    list_display = '__str__', 'balance'


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = '__str__', 'last_accessed', 'active'
