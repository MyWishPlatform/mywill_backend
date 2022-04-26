from django.contrib import admin

from .models import (
    Profile, SubSite,
    UserSiteBalance, APIToken
)

# profile
admin.site.register(Profile)
admin.site.register(SubSite)
admin.site.register(UserSiteBalance)
admin.site.register(APIToken)
