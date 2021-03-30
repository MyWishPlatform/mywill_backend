from django.contrib.admin import register, ModelAdmin

from .models import Swap


# Register your models here.
@register(Swap)
class SwapModelAdmin(ModelAdmin):
    pass
