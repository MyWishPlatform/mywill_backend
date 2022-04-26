from django.contrib import admin

from models import (
    Promo,
    User2Promo,
    Promo2ContractType
)

# promo codes
# user2promo - for specific user
# promo2contract - for specific contract
admin.site.register(Promo)
admin.site.register(User2Promo)
admin.site.register(Promo2ContractType)
