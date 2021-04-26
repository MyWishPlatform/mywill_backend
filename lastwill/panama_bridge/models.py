from django.db import models

ETH_TOKEN_ADDRESS_LENGTH = 42


class PanamaTransaction(models.Model):
    """
    Panama bridge transaction model.
    Contains data about user's transaction.
    symbol - field with TOKEN symbol in chain
    """
    SWAP_RBC = 'swap_rbc'
    SWAP_PANAMA = 'panama'
    SWAP_POLYGON = 'polygon'

    SWAP_TYPES = (
        (SWAP_RBC, SWAP_RBC.capitalize()),
        (SWAP_PANAMA, SWAP_PANAMA.capitalize()),
        (SWAP_POLYGON, SWAP_POLYGON.capitalize()),
    )

    type = models.CharField(
        max_length=50,
        verbose_name='Type',
        choices=SWAP_TYPES
    )
    from_network = models.CharField(
        max_length=4,
        verbose_name='From network',
    )
    to_network = models.CharField(
        max_length=4,
        verbose_name='To network',
    )
    actual_from_amount = models.DecimalField(
        max_digits=50,
        decimal_places=32,
        verbose_name='Actual from amount',
    )
    actual_to_amount = models.DecimalField(
        max_digits=50,
        decimal_places=32,
        verbose_name='Actual to amount',
    )
    eth_symbol = models.CharField(
        max_length=ETH_TOKEN_ADDRESS_LENGTH,
        verbose_name='ETH symbol',
    )
    bsc_symbol = models.CharField(
        max_length=ETH_TOKEN_ADDRESS_LENGTH,
        verbose_name='BSC symbol',
    )
    update_time = models.DateTimeField(
        verbose_name='Update time',
    )
    status = models.CharField(
        max_length=20,
        verbose_name='Status',
    )
    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Transaction id',
    )
    wallet_from_address = models.CharField(
        max_length=ETH_TOKEN_ADDRESS_LENGTH,
        verbose_name='Wallet from address',
    )
    wallet_to_address = models.CharField(
        max_length=ETH_TOKEN_ADDRESS_LENGTH,
        verbose_name='Wallet to address',
    )
    wallet_deposit_address = models.CharField(
        max_length=ETH_TOKEN_ADDRESS_LENGTH,
        verbose_name='Wallet deposit address',
    )
    second_transaction_id = models.CharField(
        max_length=255,
        verbose_name='Second transaction id',
        default='',
        blank=True,
    )
