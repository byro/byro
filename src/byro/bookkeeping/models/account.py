from django.db import models

from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices


class AccountCategory(Choices):
    # Regular Categories
    MEMBER_DONATION = 'member_donation'
    MEMBER_FEES = 'member_fees'

    # Categories for double-entry bookkeeping
    ASSET = 'asset'
    LIABILITY = 'liability'
    INCOME = 'income'
    EXPENSE = 'expense'

    valid_choices = [MEMBER_DONATION, MEMBER_FEES]


class Account(Auditable, models.Model):
    account_category = models.CharField(
        choices=AccountCategory.choices,
        max_length=AccountCategory.max_length,
    )
    name = models.CharField(max_length=300, null=True)  # e.g. 'Laser donations'

    class Meta:
        unique_together = (
            ('account_category', 'name'),
        )

    def __str__(self):
        if self.name:
            return self.name
        return f'{self.account_category} account #{self.id}'

    def total(self, start=None, end=None):
        incoming_sum = self.incoming_transactions.aggregate(incoming=models.Sum('amount'))['incoming']
        outgoing_sum = self.outgoing_transactions.aggregate(outgoing=models.Sum('amount'))['outgoing']
        return (incoming_sum or 0) - (outgoing_sum or 0)
