.. highlight:: python
   :linenothreshold: 5

.. _bank-transaction-importers:

Bank transaction importers
==========================

byro imports real bank transactions from files uploaded on the
"Import bank transactions" page in the finance section. Which file formats are
available depends on the installed plugins: every plugin can register one or
more *bank transaction importers*, and the user selects the importer that
matches the uploaded file (for example "CAMT.053" or "Fidor CSV").

An importer only answers one question: *which bank transactions does this file
contain?* It parses its input format and yields neutral
:class:`~byro.bookkeeping.bank_import.ImportedBankTransaction` objects. byro's
core then validates the transactions, detects duplicates, creates the
bookkeeping entries and runs the matching pipeline. An importer never creates
``Transaction`` or ``Booking`` objects, never selects bookkeeping accounts and
never matches members or fees.

.. note::

   This API is for *file based* imports. Direct bank connections such as FinTS
   need their own configuration and user interface and are therefore not
   registered as importers. They may, however, use the same
   :class:`~byro.bookkeeping.bank_import.BankTransactionImportService` to
   persist the transactions they fetch.

Minimal example
---------------

A complete importer looks like this::

    from datetime import date
    from decimal import Decimal

    from django.dispatch import receiver
    from django.utils.translation import gettext_lazy as _

    from byro.bookkeeping.bank_import import (
        BankTransactionImporter,
        ImportedBankTransaction,
        InvalidImportFile,
    )
    from byro.bookkeeping.signals import bank_transaction_importers


    class ExampleBankImporter(BankTransactionImporter):
        identifier = "byro_example.bank"
        label = _("Example Bank")

        def parse(self, source):
            with source.source_file.open("rb") as f:
                for row in parse_rows(f):  # your format specific code
                    yield ImportedBankTransaction(
                        booking_date=date(2026, 9, 1),
                        amount=Decimal("25.00"),
                        currency="EUR",
                        memo="Membership fee",
                        counterparty_name="Max Mustermann",
                        counterparty_iban="DE12 3456 7890 1234 5678 90",
                        external_id="123456789",
                    )


    @receiver(bank_transaction_importers)
    def register_example_importer(sender, **kwargs):
        return ExampleBankImporter()

Subclassing :class:`~byro.bookkeeping.bank_import.BankTransactionImporter` is
optional; any object with the attributes ``identifier`` and ``label`` and a
``parse(source)`` method is accepted. A receiver may also return a list of
importers.

Registration
------------

Connect a receiver to :data:`byro.bookkeeping.signals.bank_transaction_importers`.
The signal is sent whenever the importer selection is built or an importer is
resolved by its identifier, so registration must be cheap and side effect
free. Invalid importers and duplicate identifiers are logged and ignored.

Stable identifier
-----------------

``identifier`` is a stable, dotted string such as ``byro_camt.camt053``. It is
stored on every :class:`~byro.bookkeeping.models.RealTransactionSource` and on
every booking created from it (``Booking.importer``), and it is used for
logging and debugging. It must never depend on the translated ``label`` and
should not change once released. Prefix it with your plugin's package name to
avoid collisions with other plugins. The maximum length is 255 characters.

``parse(source)``
-----------------

``parse`` receives the :class:`~byro.bookkeeping.models.RealTransactionSource`
whose ``source_file`` holds the uploaded file. It returns an iterable (ideally
a generator) of :class:`~byro.bookkeeping.bank_import.ImportedBankTransaction`
objects.

If the file cannot be understood, raise
:class:`~byro.bookkeeping.bank_import.InvalidImportFile`, optionally with a
user presentable message. Any other exception is logged with its traceback
and reported to the user as a generic importer failure. Never put bank data
(IBANs, names, memos, raw lines) into exception messages; they are shown in
the browser.

``ImportedBankTransaction``
---------------------------

.. autoclass:: byro.bookkeeping.bank_import.ImportedBankTransaction
   :members:
   :undoc-members:

``booking_date``
    The date the bank booked the transaction (required). ``value_date``
    defaults to the booking date.

``amount``
    A :class:`~decimal.Decimal` with at most two decimal places. **Positive
    amounts are money arriving on the bank account, negative amounts are money
    leaving it.** A member paying 25 € is ``Decimal("25.00")``; the
    association paying an 80 € invoice is ``Decimal("-80.00")``. Zero amounts
    and floats are rejected. The core turns the sign into the debit/credit
    booking on the bank account, so importers do not need to know byro's
    accounting model.

``currency``
    ISO 4217 code, ``"EUR"`` by default. byro's bookkeeping has no currency
    concept, so only ``EUR`` is accepted. A transaction in any other currency
    raises :class:`~byro.bookkeeping.bank_import.UnsupportedCurrency` and
    fails the import; amounts are never silently reinterpreted as EUR.

``memo``
    The purpose / remittance information. Truncated to 1000 characters.

``counterparty_name``, ``counterparty_iban``, ``counterparty_bic``
    Information about the other party. The IBAN is normalized (upper case,
    no whitespace) before it is stored. The name is shown below the memo in
    the account and transaction views of the office.

``external_id``
    A stable reference the *bank* assigned to this transaction, for example
    the ``AcctSvcrRef`` of a CAMT entry or a provider transaction ID. If
    present, it is the primary key for duplicate detection, so it must be
    unique per bank account across all importers and must be identical every
    time the same transaction is exported. Do **not** use line numbers or
    other values that depend on the export. If your format has no such
    reference, leave it ``None`` and let the core fall back to a fingerprint.

``end_to_end_id``, ``mandate_id``, ``creditor_id``, ``bank_reference``, ``transaction_code``
    Optional SEPA and bank references. They are stored with the booking and
    contribute to the fallback fingerprint.

``data``
    Format specific metadata for this single transaction as a JSON
    serializable dict, e.g. ``{"entry_reference": "..."}``. It is stored in
    ``Booking.data`` next to the core fields listed above (the keys
    ``counterparty_name``, ``counterparty_iban``, ``counterparty_bic``,
    ``external_id``, ``end_to_end_id``, ``mandate_id``, ``creditor_id``,
    ``bank_reference`` and ``transaction_code`` are reserved for the core).
    Do not store the complete source file or the raw line for every booking:
    the original is kept in ``RealTransactionSource.source_file``, and
    duplicating it bloats the database with personal data.

What the core does
------------------

For every source processed with an importer, the
:class:`~byro.bookkeeping.bank_import.BankTransactionImportService`

1. validates and normalizes every yielded transaction,
2. computes its identity and skips transactions that are already known,
3. creates a ``Transaction`` with a single bank ``Booking`` on the special
   bank account (``SpecialAccounts.bank``) with ``source``, ``importer`` and
   ``data`` set,
4. stores the number of imported and duplicate transactions on the source,
5. runs the ``process_transaction`` matching pipeline for the new transactions.

The whole import is atomic: ``import_transactions()`` runs in a database
transaction, so if a single transaction is invalid or persisting fails,
nothing is written and the source ends in state ``FAILED``. This also holds
when the service is used directly, for example by a bank connection plugin.
Duplicates are *not* errors; a run that imports nothing new because every
transaction was already known is a successful import.

Duplicate detection
-------------------

Repeated and overlapping imports (an export for January to March followed by
one for January to April) must not create duplicate bookings, and the same
transaction may arrive through different importers over time. The core
therefore stores a SHA-256 identity on every imported booking
(``Booking.import_identity``, unique in the database) and skips transactions
whose identity already exists. Two imports running at the same time cannot
persist the same transaction twice either: the loser of the race sees a
unique constraint violation, which is counted as a duplicate.

* With an ``external_id`` the identity is derived from the bank account and
  the external ID only. It does not include the importer, so a CAMT import and
  a later import of another format carrying the same bank reference recognize
  each other.
* Without an ``external_id`` a fingerprint over the normalized booking date,
  value date, amount, currency, counterparty IBAN and name, memo and the SEPA
  references is used. Date and amount alone are never sufficient: two members
  paying the same fee on the same day are two transactions. Identical
  fingerprints *within one file* are all imported (the n-th repetition gets
  its own identity), and re-importing that file detects all of them again.

Importers do not implement any duplicate logic themselves. Everything else,
including legitimate look-alike transactions, is deliberately *not* merged:
an additional transaction is preferable to silently swallowing a payment.

Errors
------

.. automodule:: byro.bookkeeping.bank_import.api
   :members: BankTransactionImportError, UnknownImporter, InvalidImportFile, ImporterError, InvalidBankTransaction, UnsupportedCurrency
   :noindex:

``str(error)`` is always a message suitable for the user; technical details
go to the ``byro.bookkeeping.bank_import`` logger. The core logs the start,
completion (with counts) and failure (with the error class) of every import,
but never IBANs, names, memos or raw file content. Please follow the same
rule in your importer.

Import and matching are separate
--------------------------------

Importers know nothing about members, fees or bookkeeping accounts. After the
core has created the bank booking, the existing ``process_transaction``
pipeline runs unchanged, and matchers (for example one recognizing a member
number in the memo) augment the transaction. Because the core stores the
counterparty and reference fields in ``Booking.data``, matchers work the same
for every importer.

Security
--------

Uploaded bank files are untrusted input.

* Handle malformed input gracefully and raise
  :class:`~byro.bookkeeping.bank_import.InvalidImportFile` instead of letting
  arbitrary exceptions escape.
* Never execute or ``eval`` file content and never import modules based on
  file content.
* XML based formats (CAMT.053, MT94x wrappers) must disable external entities
  and DTD loading, must not perform network access while parsing and should
  limit resource usage (e.g. use ``defusedxml``). This is the plugin's
  responsibility; byro's core does not contain XML handling.
* Keep bank data out of exception messages and log lines.
* byro limits the upload size (``BANK_TRANSACTION_IMPORT_MAX_FILE_SIZE``,
  25 MiB by default) and processes each source atomically.

Legacy API
----------

Before this API existed, plugins implemented the whole import by receiving
``process_csv_upload`` and creating ``Transaction`` and ``Booking`` objects
themselves. That signal is still sent for sources without an importer (it is
offered as "Legacy bank importer (plugin)" in the selection when a receiver is
connected), so existing plugins keep working. It is deprecated for new
development, and a source processed by a new importer never triggers it.
