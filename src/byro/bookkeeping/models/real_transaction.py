from django.contrib.postgres.fields import JSONField
from django.db import models

from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices


class TransactionChannel(Choices):
    BANK = 'bank'
    CASH = 'cash'

    valid_choices = [BANK, CASH]


class RealTransaction(Auditable, models.Model):
    channel = models.CharField(
        choices=TransactionChannel.choices,
        max_length=TransactionChannel.max_length,
    )
    booking_datetime = models.DateTimeField(null=True)
    value_datetime = models.DateTimeField()
    amount = models.DecimalField(
        max_digits=8, decimal_places=2,
    )
    purpose = models.CharField(max_length=200)
    originator = models.CharField(max_length=200)
    reverses = models.ForeignKey(
        to='RealTransaction',
        on_delete=models.PROTECT,
        null=True,
    )

    importer = models.CharField(null=True, max_length=200)

    data = JSONField(null=True)

    # TODO: author/user
