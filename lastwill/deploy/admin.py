from django.contrib import admin

from .models import Network, DeployAddress

# deployment info
admin.site.register(Network)
admin.site.register(DeployAddress)
