import logging

from django.db import models, transaction
from django.utils.timezone import now

from byro.common.models import LogTargetMixin
from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices

from .transaction import Transaction

logger = logging.getLogger(__name__)


class SourceState(Choices):
    NEW = "new"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class RealTransactionSource(Auditable, models.Model, LogTargetMixin):
    LOG_TARGET_BASE = "byro.bookkeeping.real_transaction_source"

    source_file = models.FileField(upload_to="transaction_uploads/")
    state = models.CharField(
        default=SourceState.NEW,
        choices=SourceState.choices,
        max_length=SourceState.max_length,
    )
    #: Identifier of the bank transaction importer this source is processed
    #: with. Empty for legacy sources that are handled via the
    #: ``process_csv_upload`` signal.
    importer = models.CharField(max_length=255, null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    imported_count = models.PositiveIntegerField(null=True, blank=True)
    duplicate_count = models.PositiveIntegerField(null=True, blank=True)

    def process(self, user_or_context=None):
        """Process the uploaded file.

        If ``importer`` is set, the registered bank transaction importer with
        that identifier parses the file and the central import service
        persists the result (see :mod:`byro.bookkeeping.bank_import`). The
        method then returns a
        :class:`~byro.bookkeeping.bank_import.BankTransactionImportResult`.

        Otherwise the legacy ``process_csv_upload`` signal is sent, which
        must be answered by exactly one receiver; its response is returned.

        In both cases the import is all-or-nothing, the state is updated to
        ``PROCESSED`` or ``FAILED`` and errors are re-raised.
        """
        self.state = SourceState.PROCESSING
        self.save()
        try:
            with transaction.atomic():
                if self.importer:
                    response = self._process_with_importer(user_or_context)
                else:
                    response = self._process_legacy()
                self.state = SourceState.PROCESSED
                self.processed_at = now()
                self.save()
        except Exception:
            self.state = SourceState.FAILED
            self.processed_at = now()
            self.save()
            raise
        return response

    def _process_with_importer(self, user_or_context):
        from byro.bookkeeping.bank_import import (
            BankTransactionImportService,
            get_bank_transaction_importer,
        )

        importer = get_bank_transaction_importer(self.importer)
        service = BankTransactionImportService(user_or_context=user_or_context)
        result = service.import_source(self, importer)
        self.imported_count = result.imported_count
        self.duplicate_count = result.duplicate_count
        self.log(
            user_or_context or service.user_or_context,
            ".processed",
            importer=self.importer,
            imported=result.imported_count,
            duplicates=result.duplicate_count,
        )
        return result

    def _process_legacy(self):
        from byro.bookkeeping.bank_import.service import run_matching
        from byro.bookkeeping.signals import process_csv_upload

        responses = process_csv_upload.send_robust(sender=self)
        if len(responses) > 1:
            raise Exception(
                "More than one plugin tried to process the CSV upload: {}".format(
                    [r[0].__module__ + "." + r[0].__name__ for r in responses]
                )
            )
        if len(responses) < 1:
            raise Exception("No plugin tried to process the CSV upload.")
        receiver, response = responses[0]

        if isinstance(response, Exception):
            raise response

        run_matching(Transaction.objects.filter(bookings__source=self).distinct())
        return response

    @property
    def transactions(self):
        """Get all transactions."""
        return Transaction.objects.filter(bookings__source=self).distinct()

    @property
    def filename(self):
        return self.source_file.name.rsplit("/", 1)[-1] if self.source_file else ""

    def __str__(self):
        return self.filename or f"RealTransactionSource(pk={self.pk})"
