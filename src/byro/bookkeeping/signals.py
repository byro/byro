import django.dispatch

derive_virtual_transactions = django.dispatch.Signal(providing_args=[])
"""
This signal provides a RealTransaction as sender and expects a list of
one or more VirtualTransactions in response.
If no VirtualTransaction can be found, an empty list is expected. In
case of any other issues an Exception must be raised.
"""
