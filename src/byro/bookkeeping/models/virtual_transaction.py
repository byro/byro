from django.db import models

from byro.common.models.auditable import Auditable


class VirtualTransaction(Auditable, models.Model):
    real_transaction = models.ForeignKey(
        to='bookkeeping.RealTransaction',
        related_name='virtual_transactions',
        on_delete=models.PROTECT,
        null=True,
    )
    source_account = models.ForeignKey(
        to='bookkeeping.Account',
        related_name='outgoing_transactions',
        on_delete=models.PROTECT,
        null=True
    )
    destination_account = models.ForeignKey(
        to='bookkeeping.Account',
        related_name='incoming_transactions',
        on_delete=models.PROTECT,
        null=True
    )
    member = models.ForeignKey(
        to='members.Member',
        related_name='transactions',
        on_delete=models.PROTECT,
        null=True
    )

    amount = models.DecimalField(
        max_digits=8, decimal_places=2,  # TODO: enforce min_value = 0
    )
    value_datetime = models.DateTimeField(null=True)
