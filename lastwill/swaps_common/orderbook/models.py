from datetime import datetime
import random
from string import ascii_lowercase, digits

from django.contrib.auth.models import User
from django.db import models
from django.db.models.manager import Manager
from django.utils import timezone

from email_messages import swaps_deploed_subject, swaps_deploed_message
from lastwill.contracts.decorators import check_transaction
from lastwill.contracts.submodels.swaps import sendEMail
from lastwill.contracts.submodels.common import Contract, Network
from lastwill.consts import MAX_WEI_DIGITS
from lastwill.settings import SITE_PROTOCOL, SWAPS_URL


def _get_memo():
    """
        Возвращает случайно сгенерированную строку хэша.
    """
    return '0x' + ''.join(
        random.choice('abcdef'.join(digits)) for _ in range(64)
    )


def _get_unique_link():
    """
        Возвращает случайно сгенерированную строку.
    """
    return ''.join(
        random.choice(ascii_lowercase.join(digits)) for _ in range(6)
    )


class PublicActiveOrdersManager(Manager):
    def __init__(self, state, public=True):
        self.public = public
        self.state = state
        super().__init__()

    @property
    def get_state(self):
        return self.state

    def get_queryset(self):
        return super().get_queryset().filter(
            # TODO: Посмотреть можно ли сделать регистронезависимый поиск
            # для поля name.
            # name__in=[
            #     'RBC <> ETH',
            #     'ETH <> RBC',
            # ],
            public=self.public,
            state__iexact=self.get_state,
        )


class OrderBookSwaps(models.Model):
    STATE_CREATED = 'created'
    STATE_ACTIVE = 'active'
    STATE_EXPIRED = 'expired'
    STATE_POSTPONED = 'postponed'
    STATE_DONE = 'done'
    STATE_CANCELLED = 'cancelled'
    STATE_HIDDEN = 'hidden'

    ORDER_STATES = (
        (STATE_CREATED, 'CREATED'),
        (STATE_ACTIVE, 'ACTIVE'),
        (STATE_EXPIRED, 'EXPIRED'),
        (STATE_POSTPONED, 'POSTPONED'),
        (STATE_DONE, 'DONE'),
        (STATE_CANCELLED, 'CANCELLED'),
        (STATE_HIDDEN, 'HIDDEN'),
    )

    name = models.CharField(
        max_length=512,
        null=True,
        default=''
    )
    memo_contract = models.CharField(
        max_length=70,
        null=True,
        default=_get_memo
    )
    network = models.ForeignKey(
        Network,
        on_delete=models.PROTECT,
        related_name='orders',
        default=1
    )
    contract_address = models.CharField(
        max_length=255,
        verbose_name='Contract address',
        default=''
    )
    # base_coin_id = models.IntegerField(default=0)
    base_address = models.CharField(
        max_length=50,
        null=True,
        default=''
    )
    base_limit = models.DecimalField(
        max_digits=50,
        decimal_places=18,
    )
    # quote_coin_id = models.IntegerField(default=0)
    quote_address = models.CharField(
        max_length=50,
        null=True,
        default=''
    )
    quote_limit = models.DecimalField(
        max_digits=50,
        decimal_places=18,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    owner_address = models.CharField(
        max_length=50,
        null=True,
        default=''
    )
    exchange_user = models.CharField(
        max_length=512,
        null=True,
        default=''
    )
    broker_fee = models.BooleanField(default=False)
    broker_fee_address = models.CharField(
        max_length=50,
        null=True,
        default=''
    )
    broker_fee_base = models.FloatField(
        null=True,
        default=0
    )
    broker_fee_quote = models.FloatField(
        null=True,
        default=0
    )
    min_base_wei = models.CharField(
        max_length=512,
        null=True,
        default=''
    )
    min_quote_wei = models.CharField(
        max_length=512,
        null=True,
        default=''
    )
    base_amount_contributed = models.DecimalField(
        max_digits=MAX_WEI_DIGITS,
        decimal_places=0,
        default=0
    )
    base_amount_total = models.DecimalField(
        max_digits=MAX_WEI_DIGITS,
        decimal_places=0,
        default=0
    )
    quote_amount_contributed = models.DecimalField(
        max_digits=MAX_WEI_DIGITS,
        decimal_places=0,
        default=0
    )
    quote_amount_total = models.DecimalField(
        max_digits=MAX_WEI_DIGITS,
        decimal_places=0,
        default=0
    )
    public = models.BooleanField(default=True)
    unique_link = models.CharField(
        max_length=50,
        null=True,
        unique=True,
        default=_get_unique_link
    )
    created_date = models.DateTimeField(auto_now_add=True)
    stop_date = models.DateTimeField(default=timezone.now)
    contract_state = models.CharField(
        max_length=63,
        choices=ORDER_STATES,
        default=STATE_CREATED,
    )
    state = models.CharField(
        max_length=63,
        choices=ORDER_STATES,
        default=STATE_CREATED,
    )
    state_changed_at = models.DateTimeField(auto_now_add=True)
    whitelist = models.BooleanField(default=False)
    whitelist_address = models.CharField(max_length=50, null=True)
    swap_ether_contract = models.ForeignKey(Contract, null=True)
    is_exchange = models.BooleanField(default=False)
    notification = models.BooleanField(default=False)
    notification_email = models.CharField(
        max_length=50,
        null=True,
        default=''
    )
    notification_telegram_name = models.CharField(
        max_length=50,
        null=True,
        default=''
    )
    comment = models.TextField(default='')
    is_rubic_order = models.BooleanField(default=False)
    rubic_initialized = models.BooleanField(default=False)
    is_displayed = models.BooleanField(default=True)
    # !--- Managers
    objects = Manager()
    public_active_orders = PublicActiveOrdersManager(state=STATE_ACTIVE)
    # ---

    class Meta:
        indexes = (
            models.Index(
                fields=['id', 'unique_link', ]
            ),
        )

    def __str__(self):
        return f'Order "{self.name}" (unique link: {self.unique_link})'

    @check_transaction
    def msg_deployed(self):
        self.state = self.STATE_ACTIVE
        self.contract_state = self.STATE_ACTIVE
        self.save()
        if self.user.email:
            swaps_link = '{protocol}://{url}/public-v3/{unique_link}'.format(
                protocol=SITE_PROTOCOL,
                unique_link=self.unique_link,
                url=SWAPS_URL
            )
            sendEMail(
                swaps_deploed_subject,
                swaps_deploed_message.format(swaps_link=swaps_link),
                [self.user.email]
            )

    def finalized(self):
        self.state = self.STATE_DONE
        self.contract_state = self.STATE_DONE
        self.state_changed_at = datetime.utcnow()
        self.save()

    def cancelled(self):
        self.state = self.STATE_CANCELLED
        self.contract_state = self.STATE_CANCELLED
        self.state_changed_at = datetime.utcnow()
        self.save()

    def deposit_order(self, message):
        msg_amount = message['amount']
        base_address = self.base_address.lower()
        quote_address = self.quote_address.lower()
        if message['token'] == base_address or message['token'] == quote_address:
            if message['token'] == self.base_address:
                self.base_amount_contributed += msg_amount
                self.base_amount_total += msg_amount
            else:
                self.quote_amount_contributed += msg_amount
                self.quote_amount_total += msg_amount

            self.save()

    def refund_order(self, message):
        msg_amount = message['amount']
        base_address = self.base_address.lower()
        quote_address = self.quote_address.lower()
        if message['token'] == base_address or message['token'] == quote_address:
            if message['token'] == self.base_address:
                self.base_amount_contributed -= msg_amount
            else:
                self.quote_amount_contributed -= msg_amount

            self.save()

    def save(self, *args, **kwargs):
        self.base_address = self.base_address.lower()
        self.quote_address = self.quote_address.lower()
        self.owner_address = self.owner_address.lower()
        self.broker_fee_address = self.broker_fee_address.lower()

        return super().save(*args, **kwargs)
