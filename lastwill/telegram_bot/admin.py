from django.contrib import admin

from .models import BotSub

# telegram bot
@admin.register(BotSub)
class BotSubAdmin(admin.ModelAdmin):
    list_display = '__str__',
