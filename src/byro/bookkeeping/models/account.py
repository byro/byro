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
        return '{self.account_category} account #{self.id}'.format(self=self)

    @property
    def transactions(self):
        from byro.bookkeeping.models import VirtualTransaction
        return VirtualTransaction.objects.filter(
            Q(source_account=self) | Q(destination_account=self)
        )

    def total_in(self, start=None, end=now()):
        qs = self.incoming_transactions
        if start:
            qs = qs.filter(value_datetime__gte=start)
        if end:
            qs = qs.filter(value_datetime__lte=end)
        return qs.aggregate(incoming=models.Sum('amount'))['incoming'] or 0

    def total_out(self, start=None, end=now()):
        qs = self.outgoing_transactions
        if start:
            qs = qs.filter(value_datetime__gte=start)
        if end:
            qs = qs.filter(value_datetime__lte=end)
        return qs.aggregate(outgoing=models.Sum('amount'))['outgoing'] or 0

    def balance(self, start=None, end=now()):
        incoming_sum = self.total_in(start=start, end=end)
        outgoing_sum = self.total_out(start=start, end=end)
        return incoming_sum - outgoing_sum
