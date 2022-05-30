from django.contrib import admin

from .models import (
    SnapshotRow, SnapshotEOSRow,
    TRONSnapshotEth, TRONSnapshotTRON,
    TRONSnapshotEOS, TRONISHAirdropEOSISHHolders,
    TRONISHAirdropWISHHolders
)


# snapshots
@admin.register(SnapshotRow)
class SnapshotRowAdmin(admin.ModelAdmin):
    list_display = '__str__', 'value'


@admin.register(SnapshotEOSRow)
class SnapshotEOSRowAdmin(admin.ModelAdmin):
    list_display = '__str__', 'value'


@admin.register(TRONSnapshotEth)
class TRONSnapshotEthAdmin(admin.ModelAdmin):
    list_display = 'eth_address', 'tron_address', 'balance'


@admin.register(TRONSnapshotEOS)
class TRONSnapshotEOSAdmin(admin.ModelAdmin):
    list_display = 'eos_address', 'tron_address', 'balance'


@admin.register(TRONSnapshotTRON)
class TRONSnapshotTRONAdmin(admin.ModelAdmin):
    list_display = '__str__', 'balance'


@admin.register(TRONISHAirdropEOSISHHolders)
class TRONISHAirdropEOSISHHoldersAdmin(admin.ModelAdmin):
    list_display = '__str__', 'balance'


@admin.register(TRONISHAirdropWISHHolders)
class TRONISHAirdropWISHHoldersAdmin(admin.ModelAdmin):
    list_display = '__str__', 'balance'
