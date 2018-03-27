import django.dispatch

derive_virtual_transactions = django.dispatch.Signal(providing_args=[])
"""
This signal provides a RealTransaction as sender and expects a list of
one or more VirtualTransactions in response.
If no VirtualTransaction can be found, an empty list is expected. In
case of any other issues an Exception must be raised.

If the RealTransaction has already been matched, you probably should not alter
the matched VirtualTransactions or create new ones.
"""
process_csv_upload = django.dispatch.Signal(providing_args=[])
"""
This signal provides a RealTransactionSource as sender and expects a list of
one or more RealTransactions in response.

If the RealTransactionSource has already been processed, no RealTransactions
should be created, unless you are very sure what you are doing.
"""
