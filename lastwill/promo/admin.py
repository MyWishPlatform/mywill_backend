from django.contrib import admin

from .models import Promo, Promo2ContractType, User2Promo


# promo codes
# user2promo - for specific user
# promo2contract - for specific contract
@admin.register(Promo)
class PromoAdmin(admin.ModelAdmin):
    list_display = '__str__', 'start', 'stop', 'user'


@admin.register(User2Promo)
class User2Promo(admin.ModelAdmin):
    list_display = '__str__', 'created_date', 'contract_id'


@admin.register(Promo2ContractType)
class Promo2ContractTypeAdmin(admin.ModelAdmin):
    list_display = '__str__', 'discount', 'contract_type'
