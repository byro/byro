from decimal import Decimal

from django.db import models
from django.db.models import Q, OuterRef, Subquery, Value
from django.urls import reverse
from django.utils.decorators import classproperty
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.apps import apps

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


class AccountQuerySet(models.QuerySet):

    def with_balance(self, only_consider_account_id=None):
        # This query is a bit complex:
        #
        # 1. We rely on the fact, that a transaction can only have either
        #    multiple debit bookings or multiple credit bookings but not both.
        #    This is a general nececity for the database scheme to have
        #    unambigious cash flow.
        #
        # 2. First, we select all transactions and join the coresponding bookings,
        #    so we get something like this:
        #
        #     transaction_id  | debit_account_id | credit_account_id | amount
        #    -----------------+------------------+-------------------+--------
        #                  1  |               10 |                15 | 100.00
        #                  1  |               12 |                15 |  20.00
        #                  2  |             .... |               ... |    ...
        #
        #    Note: Even through transaction 1 corresponds to a single credit
        #    booking row of 120.00 € for account 15 in the database, this credit
        #    booking is splitted here into two rows. These credit parts are then
        #    joined with the debit bookings, so every row corresponds to one
        #    "cash flow" from credit_account_id to debit_account_id. This
        #    happens for all split transactions in both directions (splitted
        #    debits and splitted credits).
        #
        # 3. To obtain the correct amount for the cash flow, the lower amount of
        #    both sides (debit and credit) is taken. This works under the
        #    premise 1.
        #
        # 4. To filter for cash flows which include a certain account
        #    only_consider_account_id, the WHERE clause
        #    "(%s in (C.credit_account_id, D.debit_account_id) OR %s)" is
        #    introduced. The second variable %s is used to bypass the first
        #    clause if all all accounts should be considered. This case
        #    is associated with only_consider_account_id = None.
        #
        # 5. As we do not want to include unbalanced transactions, there is
        #    another part in the where clause, which makes sure, that both
        #    credit_account_id and dedit_account_id are not NULL for all
        #    selected rows.
        #
        # 6. As we are only interested in the accumulated cash flows, the
        #    GROUP BY statement merges the transactions per (debit, credit)
        #    account pair. This result is made available as CTE to the accounts
        #    query via the name "cash_flows".
        #
        # 7. The actual select statement for the accounts uses subqueries to
        #    the CTE result to obtain the balances.

        q = """
        WITH cash_flows AS (
            SELECT
                D.debit_account_id,
                C.credit_account_id,
                Sum(CASE
                      WHEN C.amount < D.amount OR D.amount IS NULL THEN C.amount
                      ELSE D.amount
                    END) AS amount
            FROM   "bookkeeping_transaction"
                LEFT OUTER JOIN "bookkeeping_booking" D
                             ON ( D."transaction_id" = "bookkeeping_transaction"."id"
                                  AND D."debit_account_id" IS NOT NULL )
                LEFT OUTER JOIN "bookkeeping_booking" C
                             ON ( C."transaction_id" = "bookkeeping_transaction"."id"
                                  AND C."credit_account_id" IS NOT NULL )
            WHERE
                (%s in (C.credit_account_id, D.debit_account_id)
                OR %s)
                AND C.credit_account_id IS NOT NULL
                AND D.debit_account_id IS NOT NULL
            GROUP  BY C.credit_account_id,
                   D.debit_account_id
        )
        SELECT
            *,
            (SELECT SUM(cash_flows.amount) as debit_amount
            FROM cash_flows WHERE cash_flows.debit_account_id=id),
            (SELECT SUM(cash_flows.amount) as credit_amount
            FROM cash_flows WHERE cash_flows.credit_account_id=id)
        FROM bookkeeping_account;"""

        qs = self.raw(q, [only_consider_account_id, only_consider_account_id is None])

        return qs

class AccountManager(models.Manager):
    def get_queryset(self):
        return AccountQuerySet(self.model, using=self._db)

class Account(Auditable, models.Model, LogTargetMixin):
    objects = AccountManager()

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
    def net_amount(self):
        net = None
        if self.debit_amount is not None:
            net = (net or 0) + self.debit_amount
        if self.credit_amount is not None:
            net = (net or 0) - self.credit_amount
        return net

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

    def _filter_by_date(self, qs, start, end, peer_account=None):
        if start:
            qs = qs.filter(value_datetime__gte=start)
        if end:
            qs = qs.filter(value_datetime__lte=end)
        if peer_account is not None:
            assert(peer_account != self)
            qs = qs.filter(
                Q(bookings__debit_account=peer_account) | Q(bookings__credit_account=peer_account)
            )
        return qs

    def balances(self, start=None, end=now(), peer_account=None):
        qs = self._filter_by_date(self.transactions, start, end, peer_account)

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
