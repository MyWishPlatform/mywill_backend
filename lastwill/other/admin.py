from django.contrib import admin

from .models import Sentence, ExternalService

# other - emails etc.
admin.site.register(Sentence)
admin.site.register(ExternalService)
