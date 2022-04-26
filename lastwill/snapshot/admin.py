from django.contrib import admin

from .models import (
    SnapshotRow, SnapshotEOSRow,
    TRONSnapshotEth, TRONSnapshotTRON,
    TRONSnapshotEOS, TRONISHAirdropEOSISHHolders,
    TRONISHAirdropWISHHolders
)


# snapshots
admin.site.register(SnapshotRow)
admin.site.register(SnapshotEOSRow)
admin.site.register(TRONSnapshotEth)
admin.site.register(TRONSnapshotTRON)
admin.site.register(TRONSnapshotEOS)
admin.site.register(TRONISHAirdropEOSISHHolders)
admin.site.register(TRONISHAirdropWISHHolders)
