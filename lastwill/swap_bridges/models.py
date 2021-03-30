from uuid import uuid4

from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    DecimalField,
    Model,
    UUIDField,
)
from django.db.models.fields import PositiveIntegerField

class Swap(Model):
    CREATED = 'created'
    PENDING = 'pending'
    SUCCESS = 'success'
    FAIL = 'fail'

    SWAP_STATUSES = (
        (CREATED, CREATED.capitalize()),
        (PENDING, PENDING.capitalize()),
        (SUCCESS, SUCCESS.capitalize()),
        (FAIL, FAIL.capitalize()),
    )

    id = UUIDField(
        primary_key=True,
        editable=False,
        verbose_name='Id',
        default=uuid4
    )
    source_network = PositiveIntegerField(
        verbose_name='Source network (1: BSC; 2: ETH)',
    )
    target_network = PositiveIntegerField(
        verbose_name='Target network (1: BSC; 2: ETH)',
    )
    token = CharField(
        max_length=255,
        verbose_name='Token',
    )
    source_address = CharField(
        max_length=255,
        verbose_name='Source address',
    )
    target_address = CharField(
        max_length=255,
        verbose_name='Target address',
    )
    amount = DecimalField(
        max_digits=100,
        decimal_places=0,
        verbose_name='Amount',
    )
    fee_address = CharField(
        max_length=255,
        verbose_name='Fee address',
    )
    fee_amount = DecimalField(
        max_digits=100,
        decimal_places=0,
        verbose_name='Fee amount',
    )
    tx_hash = CharField(
        max_length=255,
        verbose_name='Tx hash',
    )
    status = CharField(
        max_length=255,
        choices=SWAP_STATUSES,
        verbose_name='Status',
        default=CREATED,
    )
    create_at = DateTimeField(
        auto_now_add=True,
        verbose_name='Create at',
    )
    update_at = DateTimeField(
        auto_now=True,
        verbose_name='Update at',
    )
    is_displayed = BooleanField(
        default=True,
        verbose_name='Is displayed',
    )

    class Meta:
        db_table = 'swaps'
