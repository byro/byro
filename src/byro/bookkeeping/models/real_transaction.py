from django.contrib.postgres.fields import JSONField
from django.db import models, transaction

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

    @transaction.atomic
    def derive_virtual_transactions(self):
        """
        Collects responses to the signal `derive_virtual_transactions`. Raises an
        exception if multiple results were found, and re-raises received Exceptions.

        Returns a list of one or more VirtualTransaction objects if no Exception
        was raised.
        """
        from byro.bookkeeping.signals import derive_virtual_transactions
        responses = derive_virtual_transactions.send_robust(sender=self)
        if len(responses) > 1:
            raise Exception('More than one plugin tried to derive virtual transactions.')
        if len(responses) < 1:
            raise Exception('No plugin tried to derive virtual transactions.')
        receiver, response = responses[0]

        if isinstance(response, Exception):
            raise response

        if not isinstance(response, list) or len(response) == 0:
            raise Exception('Transaction could not be matched')

        return response  # TODO: sanity check response for virtual transaction objects

