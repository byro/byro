import django.dispatch

process_transaction = django.dispatch.Signal()
"""
This signal provides a Transaction as sender and expects the receiver
to augment the Transaction with auto-detected information as appropriate.

The common case is a Transaction that is unbalanced and can be augmented
to be a balanced Transaction by adding one or more Bookings.

Recipients MUST NOT change any data in the Transaction or its Bookings if
Transaction.is_read_only is True.
"""

bank_transaction_importers = django.dispatch.Signal()
"""
This signal allows you to register bank transaction importers that appear in
the importer selection of the "Import bank transactions" page.
Receives None as sender. Must return a single importer object or an iterable
of importer objects. An importer provides a stable ``identifier``, a
translatable ``label`` and a ``parse(source)`` method that yields
:class:`byro.bookkeeping.bank_import.ImportedBankTransaction` objects for the
given :class:`~byro.bookkeeping.models.RealTransactionSource`::

    @receiver(bank_transaction_importers)
    def register_importer(sender, **kwargs):
        return ExampleBankImporter()

See :doc:`/developer/plugins/bank-transaction-importers` for the complete
contract. Importers must not create Transaction or Booking objects
themselves; byro's core persists the yielded transactions, detects
duplicates and runs the ``process_transaction`` matching afterwards.
"""

process_csv_upload = django.dispatch.Signal()
"""
**Legacy API, deprecated for new development.** Use
``bank_transaction_importers`` instead.

This signal provides a RealTransactionSource as sender and expects a list of
one or more Transactions in response. It is only sent for sources that were
not assigned a bank transaction importer (``RealTransactionSource.importer``
is empty), and exactly one receiver must be connected.

If the RealTransactionSource has already been processed, no Transactions
should be created, unless you are very sure what you are doing.
"""
