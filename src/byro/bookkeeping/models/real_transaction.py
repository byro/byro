from django.db import models, transaction

from byro.common.models import LogTargetMixin
from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices

from .transaction import Transaction


class SourceState(Choices):
    NEW = "new"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class RealTransactionSource(Auditable, models.Model, LogTargetMixin):
    source_file = models.FileField(upload_to="transaction_uploads/")
    state = models.CharField(
        default=SourceState.NEW,
        choices=SourceState.choices,
        max_length=SourceState.max_length,
    )

    @transaction.atomic
    def process(self):
        """
        Collects responses to the signal `process_csv_upload`. Raises an
        exception if multiple results were found, and re-raises received Exceptions.

        Returns a list of one or more Transaction objects if no Exception
        was raised.
        """
        self.state = SourceState.PROCESSING
        self.save()
        from byro.bookkeeping.signals import process_csv_upload

        responses = process_csv_upload.send_robust(sender=self)
        if len(responses) > 1:
            self.state = SourceState.FAILED
            self.save()
            raise Exception(
                "More than one plugin tried to process the CSV upload: {}".format(
                    [r[0].__module__ + "." + r[0].__name__ for r in responses]
                )
            )
        if len(responses) < 1:
            self.state = SourceState.FAILED
            self.save()
            raise Exception("No plugin tried to process the CSV upload.")
        receiver, response = responses[0]

        if isinstance(response, Exception):
            self.state = SourceState.FAILED
            self.save()
            raise response

        for t in Transaction.objects.filter(bookings__source=self):
            try:
                t.process_transaction()
            except Exception as e:
                print(e)  # FIXME

        self.state = SourceState.PROCESSED
        self.save()
        return response
