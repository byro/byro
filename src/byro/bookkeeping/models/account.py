from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.decorators import classproperty
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from byro.common.models import LogTargetMixin
from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices


class AccountCategory(Choices):
    # Categories for double-entry bookkeeping
    ASSET = "asset"  # de: Aktiva, for example your bank account or cash
    LIABILITY = "liability"  # de: Passiva, for example invoices you have to pay
    INCOME = "income"  # de: Ertragskonten, for example for fees paid
    EXPENSE = "expense"  # de: Aufwandskonten, for example for fees to be paid
    EQUITY = "equity"  # de: Eigenkapital, assets less liabilities

    @classproperty
    def choices(cls):
        return (
            (cls.ASSET, _("Asset account")),
            (cls.LIABILITY, _("Liability account")),
            (cls.INCOME, _("Income account")),
            (cls.EXPENSE, _("Expense account")),
            (cls.EQUITY, _("Equity account")),
        )


class AccountTag(models.Model):
    name = models.CharField(max_length=300, null=False, unique=True)
    description = models.CharField(max_length=1000, null=True)

    def __str__(self):
        return self.name


class Account(Auditable, models.Model, LogTargetMixin):
    account_category = models.CharField(
        choices=AccountCategory.choices, max_length=AccountCategory.max_length
    )
    name = models.CharField(max_length=300, null=True)  # e.g. 'Laser donations'
    tags = models.ManyToManyField(AccountTag, related_name="accounts")

    class Meta:
        unique_together = (("account_category", "name"),)

    def __str__(self):
        if self.name:
            return self.name
        return "{self.account_category} account #{self.id}".format(self=self)

    @property
    def bookings(self):
        from byro.bookkeeping.models import Booking

        return Booking.objects.filter(Q(debit_account=self) | Q(credit_account=self))

    @property
    def bookings_with_transaction_data(self):
        from byro.bookkeeping.models import Booking

        return Booking.objects.with_transaction_data().filter(
            Q(debit_account=self) | Q(credit_account=self)
        )

    @property
    def transactions(self):
        from byro.bookkeeping.models import Transaction

        return Transaction.objects.filter(
            Q(bookings__debit_account=self) | Q(bookings__credit_account=self)
        )

    @property
    def unbalanced_transactions(self):
        from byro.bookkeeping.models import Transaction

        return Transaction.objects.unbalanced_transactions().filter(
            Q(bookings__debit_account=self) | Q(bookings__credit_account=self)
        )

    def _filter_by_date(self, qs, start, end):
        if start:
            qs = qs.filter(value_datetime__gte=start)
        if end:
            qs = qs.filter(value_datetime__lte=end)
        return qs

    def balances(self, start=None, end=now()):
        qs = self._filter_by_date(self.transactions, start, end)

        result = qs.with_balances().aggregate(
            debit=models.functions.Coalesce(models.Sum("balances_debit"), 0),
            credit=models.functions.Coalesce(models.Sum("balances_credit"), 0),
        )

        # ASSET, EXPENSE:  Debit increases balance, credit decreases it
        # INCOME, LIABILITY, EQUITY:  Debit decreases balance, credit increases it

        if self.account_category in (
            AccountCategory.LIABILITY,
            AccountCategory.INCOME,
            AccountCategory.EQUITY,
        ):
            result["net"] = result["credit"] - result["debit"]
        else:
            result["net"] = result["debit"] - result["credit"]

        result = {k: Decimal(v).quantize(Decimal("0.01")) for k, v in result.items()}

        return result

    def get_absolute_url(self):
        return reverse("office:finance.accounts.detail", kwargs={"pk": self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-bank"></i> ')
