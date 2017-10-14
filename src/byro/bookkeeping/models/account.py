from django.db import models
from django.db.models import Q
from django.utils.decorators import classproperty
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

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

    @classproperty
    def choices(cls):
        return (
            (cls.MEMBER_DONATION, _('Donation account')),
            (cls.MEMBER_FEES, _('Membership fee account')),
            (cls.ASSET, _('Asset account')),
            (cls.LIABILITY, _('Liability account')),
            (cls.INCOME, _('Income account')),
            (cls.EXPENSE, _('Expense account')),
        )


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

    def balance(self, start=None, end=None):
        incoming_sum = self.incoming_transactions.aggregate(incoming=models.Sum('amount'))['incoming']
        outgoing_sum = self.outgoing_transactions.aggregate(outgoing=models.Sum('amount'))['outgoing']
        return (incoming_sum or 0) - (outgoing_sum or 0)
