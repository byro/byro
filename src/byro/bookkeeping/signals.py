import django.dispatch

process_transaction = django.dispatch.Signal(providing_args=[])
"""
This signal provides a Transaction as sender and expects the receiver
to augment the Transaction with auto-detected information as appropriate.

The common case is a Transaction that is unbalanced and can be augmented
to be a balanced Transaction by adding one or more Bookings.

Recipients MUST NOT change any data in the Transaction or its Bookings if
Transaction.is_read_only is True.
"""

process_csv_upload = django.dispatch.Signal(providing_args=[])
"""
This signal provides a RealTransactionSource as sender and expects a list of
one or more Transactions in response.

If the RealTransactionSource has already been processed, no Transactions
should be created, unless you are very sure what you are doing.
"""
