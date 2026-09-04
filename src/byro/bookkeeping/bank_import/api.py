"""Public API for bank transaction importers.

Plugins that want to import bank transactions from a file implement a
:class:`BankTransactionImporter` and register it via the
``byro.bookkeeping.signals.bank_transaction_importers`` signal. The importer
only parses its input and yields :class:`ImportedBankTransaction` objects;
byro's :class:`~byro.bookkeeping.bank_import.service.BankTransactionImportService`
takes care of validation, duplicate detection, persistence and matching.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Iterable

from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:  # pragma: no cover
    from byro.bookkeeping.models import RealTransactionSource, Transaction

#: Currencies the central import service accepts. byro's bookkeeping has no
#: currency concept, so only the association's accounting currency is allowed.
SUPPORTED_CURRENCIES = ("EUR",)

#: Maximum length of an importer identifier (matches the database column).
MAX_IDENTIFIER_LENGTH = 255


@dataclass(frozen=True)
class ImportedBankTransaction:
    """Neutral description of a single bank transaction.

    This is the contract between a format specific parser and byro's
    bookkeeping. It is intentionally not a Django model.

    Amount semantics: ``amount > 0`` is money arriving on the bank account,
    ``amount < 0`` is money leaving the bank account.
    """

    booking_date: datetime.date
    amount: Decimal

    value_date: datetime.date | None = None
    currency: str = "EUR"

    memo: str = ""

    counterparty_name: str | None = None
    counterparty_iban: str | None = None
    counterparty_bic: str | None = None

    #: Stable, bank assigned reference for this transaction (for example the
    #: CAMT ``AcctSvcrRef``). Must be unique per bank account across all
    #: importers. Leave ``None`` if the format has no reliable identifier.
    external_id: str | None = None

    end_to_end_id: str | None = None
    mandate_id: str | None = None
    creditor_id: str | None = None
    bank_reference: str | None = None

    transaction_code: str | None = None

    #: Format specific metadata for this single transaction. Must be JSON
    #: serialisable. Never put the complete source file here.
    data: dict = field(default_factory=dict)


class BankTransactionImporter:
    """Base class for bank transaction importers.

    Subclassing is optional; any object providing ``identifier``, ``label``
    and ``parse()`` with the same semantics is accepted.
    """

    #: Stable, dotted identifier, e.g. ``"byro_camt.camt053"``. Stored on
    #: every import and booking, must never depend on the translated label.
    identifier: str = ""
    #: Human readable (translatable) label shown in the importer selection.
    label: str = ""

    def parse(
        self, source: "RealTransactionSource"
    ) -> Iterable[ImportedBankTransaction]:
        """Parse ``source.source_file`` and yield the contained transactions.

        Raise :class:`InvalidImportFile` if the file cannot be understood.
        """
        raise NotImplementedError


@dataclass
class BankTransactionImportResult:
    """Outcome of a successful import run."""

    imported_count: int = 0
    duplicate_count: int = 0
    transactions: list["Transaction"] = field(default_factory=list)

    @property
    def read_count(self) -> int:
        return self.imported_count + self.duplicate_count


class BankTransactionImportError(Exception):
    """Base class for all errors raised by the bank transaction import.

    ``str(error)`` is a user presentable message that must not contain bank
    data. Technical details belong into the log.
    """

    default_message = _("The bank transaction import failed.")

    def __init__(self, message=None, **kwargs):
        self.message = message or self.default_message
        super().__init__(self.message)

    def __str__(self):
        return str(self.message)


class UnknownImporter(BankTransactionImportError):
    default_message = _("The selected bank transaction importer is not available.")

    def __init__(self, identifier=None, message=None):
        self.identifier = identifier
        super().__init__(message)


class InvalidImportFile(BankTransactionImportError):
    """The importer could not interpret the uploaded file."""

    default_message = _(
        "The file could not be processed by the selected bank transaction importer."
    )


class ImporterError(BankTransactionImportError):
    """The importer failed unexpectedly."""

    default_message = _(
        "The selected bank transaction importer failed unexpectedly. "
        "Details have been written to the log."
    )


class InvalidBankTransaction(BankTransactionImportError):
    """An importer yielded a transaction the core cannot persist."""

    default_message = _("The file contains an invalid bank transaction.")

    def __init__(self, message=None, position=None):
        self.position = position
        super().__init__(message)


class UnsupportedCurrency(InvalidBankTransaction):
    default_message = _("The file contains a transaction in an unsupported currency.")

    def __init__(self, currency, position=None):
        self.currency = currency
        super().__init__(
            _(
                "The file contains a transaction in the unsupported currency %(currency)s."
            )
            % {"currency": currency},
            position=position,
        )
