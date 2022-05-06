from django.contrib import admin

from .models import Sentence, ExternalService


# other - emails etc.
@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = '__str__', 'email', 'contract_name'


@admin.register(ExternalService)
class ExternalService(admin.ModelAdmin):
    list_display = '__str__',
