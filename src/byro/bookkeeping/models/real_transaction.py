from django.contrib.postgres.fields import JSONField
from django.db import models, transaction

from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices


class SourceState(Choices):
    NEW = 'new'
    PROCESSING = 'processing'
    PROCESSED = 'processed'
    FAILED = 'failed'

    valid_choices = [NEW, PROCESSING, PROCESSED, FAILED]


class RealTransactionSource(Auditable, models.Model):
    source_file = models.FileField(upload_to='transaction_uploads/')
    state = models.CharField(default=SourceState.NEW, choices=SourceState.choices, max_length=SourceState.max_length)

    @transaction.atomic
    def process(self):
        """
        Collects responses to the signal `process_csv_upload`. Raises an
        exception if multiple results were found, and re-raises received Exceptions.

        Returns a list of one or more RealTransaction objects if no Exception
        was raised.
        """
        self.state = SourceState.PROCESSING
        self.save()
        from byro.bookkeeping.signals import process_csv_upload
        responses = process_csv_upload.send_robust(sender=self)
        if len(responses) > 1:
            self.state = SourceState.FAILED
            self.save()
            raise Exception('More than one plugin tried to process the CSV upload: {}'.format([r[0].__module__ + '.' + r[0].__name__ for r in responses]))
        if len(responses) < 1:
            self.state = SourceState.FAILED
            self.save()
            raise Exception('No plugin tried to process the CSV upload.')
        receiver, response = responses[0]

        if isinstance(response, Exception):
            self.state = SourceState.FAILED
            self.save()
            raise response
        self.state = SourceState.PROCESSED
        self.save()
        return response


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
    purpose = models.CharField(max_length=1000)
    originator = models.CharField(max_length=500)
    reverses = models.ForeignKey(
        to='RealTransaction',
        on_delete=models.PROTECT,
        null=True,
    )
    importer = models.CharField(null=True, max_length=500)
    data = JSONField(null=True)
    source = models.ForeignKey(
        to=RealTransactionSource,
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True,
    )

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
            raise Exception('More than one plugin tried to derive virtual transactions: {}'.format([r[0].__module__ + '.' + r[0].__name__ for r in responses]))
        if len(responses) < 1:
            raise Exception('No plugin tried to derive virtual transactions.')
        receiver, response = responses[0]

        if isinstance(response, Exception):
            raise response

        if not isinstance(response, list) or len(response) == 0:
            raise Exception('Transaction could not be matched')

        return response  # TODO: sanity check response for virtual transaction objects
