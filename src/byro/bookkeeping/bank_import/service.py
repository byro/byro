"""Central import service turning :class:`ImportedBankTransaction` objects
into byro bookkeeping entries."""

import datetime
import json
import logging
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from byro.bookkeeping.models import Booking, Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts

from . import identity as identity_module
from .api import (
    SUPPORTED_CURRENCIES,
    BankTransactionImportError,
    BankTransactionImportResult,
    ImportedBankTransaction,
    ImporterError,
    InvalidBankTransaction,
    UnsupportedCurrency,
)

logger = logging.getLogger(__name__)

#: Default log context used when no user or request is available.
DEFAULT_CONTEXT = "byro.bookkeeping.bank_import"

MAX_MEMO_LENGTH = Booking._meta.get_field("memo").max_length
MAX_AMOUNT = Decimal(10) ** (
    Booking._meta.get_field("amount").max_digits
    - Booking._meta.get_field("amount").decimal_places
)
_CENT = Decimal("0.01")
_IN_CHUNK_SIZE = 500

#: Keys of ``Booking.data`` that are written by the core. Importer specific
#: ``data`` must not use these keys; core values take precedence.
RESERVED_DATA_KEYS = (
    "counterparty_name",
    "counterparty_iban",
    "counterparty_bic",
    "external_id",
    "end_to_end_id",
    "mandate_id",
    "creditor_id",
    "bank_reference",
    "transaction_code",
)


@dataclass
class _NormalizedTransaction:
    position: int
    booking_datetime: datetime.datetime
    value_datetime: datetime.datetime
    amount: Decimal
    memo: str
    identity: str
    data: dict


def run_matching(transactions):
    """Run the ``process_transaction`` pipeline for freshly imported
    transactions.

    Matching failures (including "no plugin augmented the transaction") are
    not import failures: the transaction stays unbalanced and can be matched
    manually later.
    """
    for t in transactions:
        try:
            t.process_transaction()
        except Exception as e:
            logger.debug("Matching skipped for transaction %s: %s", t.pk, e)


class BankTransactionImportService:
    """Validate, deduplicate and persist imported bank transactions.

    :meth:`import_transactions` (and therefore :meth:`import_source`) runs in
    a database transaction: either all new transactions are persisted or none.
    """

    def __init__(self, user_or_context=None):
        self.user_or_context = user_or_context or DEFAULT_CONTEXT

    # -- orchestration -----------------------------------------------------

    def import_source(self, source, importer, match=True):
        """Parse ``source`` with ``importer`` and import the result.

        Writes structured log entries and returns a
        :class:`BankTransactionImportResult`.
        """
        logger.info(
            "Bank transaction import started source=%s importer=%s",
            source.pk,
            importer.identifier,
        )
        try:
            result = self.import_transactions(
                source, self._parse(source, importer), importer
            )
        except BankTransactionImportError as e:
            logger.warning(
                "Bank transaction import failed source=%s importer=%s error=%s position=%s",
                source.pk,
                importer.identifier,
                type(e).__name__,
                getattr(e, "position", None),
            )
            raise
        logger.info(
            "Bank transaction import completed source=%s importer=%s imported=%s duplicates=%s",
            source.pk,
            importer.identifier,
            result.imported_count,
            result.duplicate_count,
        )
        if match:
            run_matching(result.transactions)
        return result

    def _parse(self, source, importer):
        try:
            yield from importer.parse(source)
        except BankTransactionImportError:
            raise
        except Exception as e:
            logger.exception(
                "Bank transaction importer %s raised while parsing source=%s",
                importer.identifier,
                source.pk,
            )
            raise ImporterError() from e

    # -- import ------------------------------------------------------------

    @transaction.atomic
    def import_transactions(self, source, transactions, importer):
        """Persist ``transactions`` (an iterable of
        :class:`ImportedBankTransaction`) as bank bookings.

        All transactions are validated before anything is written, and the
        whole import is atomic. Known transactions (see
        :mod:`byro.bookkeeping.bank_import.identity`) are counted as
        duplicates and skipped; they are not an error. This includes
        transactions persisted by a concurrent import in the meantime, which
        are caught by the unique constraint on ``Booking.import_identity``.
        """
        bank_account = SpecialAccounts.bank
        account_context = str(bank_account.pk)
        importer_id = importer.identifier

        normalized = []
        fingerprints = Counter()
        seen = set()
        duplicate_count = 0
        for position, imported in enumerate(transactions, start=1):
            entry = self._normalize(imported, position, account_context, fingerprints)
            if entry.identity in seen:
                duplicate_count += 1
                continue
            seen.add(entry.identity)
            normalized.append(entry)

        existing = self._existing_identities(seen)
        result = BankTransactionImportResult(duplicate_count=duplicate_count)
        for entry in normalized:
            if entry.identity in existing:
                result.duplicate_count += 1
                continue
            try:
                with transaction.atomic():
                    t = self._persist(entry, bank_account, source, importer_id)
            except IntegrityError:
                # Another import persisted this transaction after we checked
                # for existing identities. Treat it as a duplicate.
                if not Booking.objects.filter(import_identity=entry.identity).exists():
                    raise
                logger.info(
                    "Bank transaction import skipped concurrently imported "
                    "transaction source=%s position=%s",
                    source.pk,
                    entry.position,
                )
                result.duplicate_count += 1
                continue
            result.transactions.append(t)
            result.imported_count += 1
        return result

    def _existing_identities(self, identities):
        identities = list(identities)
        existing = set()
        for start in range(0, len(identities), _IN_CHUNK_SIZE):
            chunk = identities[start : start + _IN_CHUNK_SIZE]
            existing.update(
                Booking.objects.filter(import_identity__in=chunk).values_list(
                    "import_identity", flat=True
                )
            )
        return existing

    # -- validation and normalisation ---------------------------------------

    def _normalize(self, imported, position, account_context, fingerprints):
        if not isinstance(imported, ImportedBankTransaction):
            raise InvalidBankTransaction(
                _("Entry %(position)s is not an imported bank transaction.")
                % {"position": position},
                position=position,
            )

        currency = identity_module.normalize_currency(imported.currency)
        if currency not in SUPPORTED_CURRENCIES:
            raise UnsupportedCurrency(currency or "", position=position)

        amount = self._validate_amount(imported.amount, position)
        booking_datetime = self._to_datetime(
            imported.booking_date, position, "booking_date"
        )
        value_datetime = (
            self._to_datetime(imported.value_date, position, "value_date")
            if imported.value_date is not None
            else booking_datetime
        )
        memo = self._validate_memo(imported.memo, position)
        data = self._build_data(imported, position)

        external_id = identity_module.normalize_reference(imported.external_id)
        if external_id:
            identity = identity_module.external_identity(account_context, external_id)
        else:
            base = identity_module.fingerprint_identity(account_context, imported)
            occurrence = fingerprints[base]
            fingerprints[base] += 1
            identity = (
                base
                if occurrence == 0
                else identity_module.fingerprint_identity(
                    account_context, imported, occurrence=occurrence
                )
            )

        return _NormalizedTransaction(
            position=position,
            booking_datetime=booking_datetime,
            value_datetime=value_datetime,
            amount=amount,
            memo=memo,
            identity=identity,
            data=data,
        )

    def _validate_amount(self, amount, position):
        error = InvalidBankTransaction(
            _("Transaction %(position)s has an invalid amount.")
            % {"position": position},
            position=position,
        )
        if isinstance(amount, (float, bool)) or amount is None:
            raise error
        if not isinstance(amount, Decimal):
            try:
                amount = Decimal(str(amount))
            except (InvalidOperation, ValueError, TypeError):
                raise error from None
        if not amount.is_finite() or amount == 0:
            raise error
        if amount != amount.quantize(_CENT) or abs(amount) >= MAX_AMOUNT:
            raise error
        return amount.quantize(_CENT)

    def _to_datetime(self, value, position, field_name):
        if isinstance(value, datetime.datetime):
            result = value
        elif isinstance(value, datetime.date):
            result = datetime.datetime.combine(value, datetime.time.min)
        else:
            raise InvalidBankTransaction(
                _("Transaction %(position)s has an invalid date.")
                % {"position": position},
                position=position,
            )
        if timezone.is_naive(result):
            result = timezone.make_aware(result)
        return result

    def _validate_memo(self, memo, position):
        if memo is None:
            return ""
        if not isinstance(memo, str):
            raise InvalidBankTransaction(
                _("Transaction %(position)s has an invalid memo.")
                % {"position": position},
                position=position,
            )
        return memo.strip()[:MAX_MEMO_LENGTH]

    def _build_data(self, imported, position):
        extra = imported.data
        if extra is None:
            extra = {}
        if not isinstance(extra, dict):
            raise InvalidBankTransaction(
                _("Transaction %(position)s has invalid metadata.")
                % {"position": position},
                position=position,
            )
        try:
            json.dumps(extra)
        except (TypeError, ValueError):
            raise InvalidBankTransaction(
                _("Transaction %(position)s has metadata that cannot be stored.")
                % {"position": position},
                position=position,
            ) from None

        core = {
            "counterparty_name": identity_module.normalize_text(
                imported.counterparty_name
            ),
            "counterparty_iban": identity_module.normalize_iban(
                imported.counterparty_iban
            ),
            "counterparty_bic": identity_module.normalize_reference(
                imported.counterparty_bic
            ),
            "external_id": identity_module.normalize_reference(imported.external_id),
            "end_to_end_id": identity_module.normalize_reference(
                imported.end_to_end_id
            ),
            "mandate_id": identity_module.normalize_reference(imported.mandate_id),
            "creditor_id": identity_module.normalize_reference(imported.creditor_id),
            "bank_reference": identity_module.normalize_reference(
                imported.bank_reference
            ),
            "transaction_code": identity_module.normalize_text(
                imported.transaction_code
            ),
        }
        data = dict(extra)
        data.update({k: v for k, v in core.items() if v is not None})
        return data

    # -- persistence -------------------------------------------------------

    def _persist(self, entry, bank_account, source, importer_id):
        t = Transaction.objects.create(
            memo=entry.memo or None,
            booking_datetime=entry.booking_datetime,
            value_datetime=entry.value_datetime,
            user_or_context=self.user_or_context,
        )
        booking_kwargs = dict(
            amount=abs(entry.amount),
            memo=entry.memo or None,
            booking_datetime=entry.booking_datetime,
            importer=importer_id,
            source=source,
            import_identity=entry.identity,
            data=entry.data,
            user_or_context=self.user_or_context,
        )
        if entry.amount > 0:
            t.debit(account=bank_account, **booking_kwargs)
        else:
            t.credit(account=bank_account, **booking_kwargs)
        return t
