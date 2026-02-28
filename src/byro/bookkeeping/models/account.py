from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.functional import classproperty
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

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
    associated = models.ForeignKey("Account", null=True, on_delete=models.SET_NULL)

    def associate(self, other):
        # allowed associations are only:
        #   income <--> asset
        #   expense <--> liability
        allowed_association_categories = [
            {AccountCategory.INCOME, AccountCategory.ASSET},
            {AccountCategory.EXPENSE, AccountCategory.LIABILITY}
        ]

        if other is not None and {self.account_category, other.account_category} not in allowed_association_categories:
            raise Exception("Associating categories " + self.account_category + " and " + other.account_category + " is not allowed.")

        if self.associated is not None:
            self.associated.associated = None

        self.associated = other
        if other is not None:
            other.associated = self

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

    def balances(self, start=None, end=None):
        end = end or now()
        qs = self._filter_by_date(self.transactions, start, end)

        result = qs.with_balances().aggregate(
            debit=models.functions.Coalesce(
                models.Sum("balances_debit"), 0, output_field=models.DecimalField()
            ),
            credit=models.functions.Coalesce(
                models.Sum("balances_credit"), 0, output_field=models.DecimalField()
            ),
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

    def balances_with_associated(self, start=None, end=now()):
        if self.account_category not in [AccountCategory.INCOME, AccountCategory.EXPENSE]:
            raise Exception("This is only allowed for income or expense accounts.")

        result_1 = self.balances(start, end)
        if self.associated is None:
            return result_1

        result_2 = self.associated.balances(start, end)

        if self.account_category == AccountCategory.INCOME:
            result = {
                "net": result_1['net'] - result_2['net'],
                "debit": result_1['debit'],
                "credit": result_1['credit'] - result_2['net']
            }
        else:
            result = {
                "net": result_1['net'] - result_2['net'],
                "debit": result_1['debit'] - result_2['net'],
                "credit": result_1['credit']
            }

        return result

    def get_absolute_url(self):
        return reverse("office:finance.accounts.detail", kwargs={"pk": self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-bank"></i> ')
