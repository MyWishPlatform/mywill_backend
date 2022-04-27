from django.contrib import admin

from .models import Network, DeployAddress


# deployment info
@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = '__str__'


@admin.register(DeployAddress)
class DeployAddressAdmin(admin.ModelAdmin):
    list_display = '__str__'
