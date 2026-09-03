"""Canonicalisation and identity (duplicate detection) for imported bank
transactions.

The identity of an imported transaction is a SHA-256 digest that is stored on
the resulting bank booking. Two transactions with the same identity are the
same bank transaction, regardless of the importer that delivered them.

* If the importer provides a stable ``external_id`` (a bank assigned
  reference), the identity is derived from the bank account and that ID.
* Otherwise a fingerprint over the normalised transaction attributes is used.

The identity must never depend on the importer identifier or the source file,
so that overlapping exports and different importers delivering the same
transaction are recognised as duplicates.
"""

import hashlib
import re
from decimal import Decimal

_WHITESPACE = re.compile(r"\s+")

#: Version tag mixed into every digest. Bump when the canonical
#: representation changes incompatibly (existing bookings will then no
#: longer be recognised as duplicates).
IDENTITY_VERSION = "byro.bank_import.v1"


def normalize_iban(value):
    if value is None:
        return None
    value = _WHITESPACE.sub("", str(value)).upper()
    return value or None


def normalize_currency(value):
    if value is None:
        return None
    return str(value).strip().upper() or None


def normalize_text(value):
    """Collapse whitespace and strip. Returns ``None`` for empty values."""
    if value is None:
        return None
    value = _WHITESPACE.sub(" ", str(value)).strip()
    return value or None


def normalize_reference(value):
    """Normalise identifiers such as end-to-end IDs or bank references."""
    if value is None:
        return None
    value = _WHITESPACE.sub("", str(value))
    return value or None


def normalize_amount(value):
    """Return the amount as a plain decimal string (``"25.00"``)."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return format(value.quantize(Decimal("0.01")), "f")


def _digest(*parts):
    canonical = "\x1f".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def external_identity(account_context, external_id):
    """Identity for a transaction with a stable bank assigned reference."""
    return _digest(IDENTITY_VERSION, "external", account_context, external_id)


def fingerprint_identity(account_context, transaction, occurrence=0):
    """Fallback identity for transactions without an external ID.

    ``occurrence`` distinguishes otherwise identical transactions within one
    import run (the n-th repetition of the same fingerprint), so that two
    legitimately identical payments in one statement are both imported while
    a repeated import of the same statement still detects both as duplicates.
    """
    casefold = lambda v: v.casefold() if v is not None else None  # noqa: E731
    return _digest(
        IDENTITY_VERSION,
        "fingerprint",
        account_context,
        transaction.booking_date.isoformat(),
        transaction.value_date.isoformat() if transaction.value_date else None,
        normalize_amount(transaction.amount),
        normalize_currency(transaction.currency),
        normalize_iban(transaction.counterparty_iban),
        casefold(normalize_text(transaction.counterparty_name)),
        casefold(normalize_text(transaction.memo)),
        normalize_reference(transaction.end_to_end_id),
        normalize_reference(transaction.mandate_id),
        normalize_reference(transaction.creditor_id),
        normalize_reference(transaction.bank_reference),
        occurrence or None,
    )
