from collections import Counter

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.safestring import mark_safe

from byro.common.models import LogTargetMixin, log_call
from byro.documents.models import Document


class TransactionQuerySet(models.QuerySet):
    def with_balances(self):
        qs = self.annotate(
            balances_debit=models.Sum(
                models.Case(
                    models.When(
                        ~models.Q(bookings__debit_account=None), then="bookings__amount"
                    ),
                    default=0,
                    output_field=models.DecimalField(max_digits=8, decimal_places=2),
                )
            ),
            balances_credit=models.Sum(
                models.Case(
                    models.When(
                        ~models.Q(bookings__credit_account=None),
                        then="bookings__amount",
                    ),
                    default=0,
                    output_field=models.DecimalField(max_digits=8, decimal_places=2),
                )
            ),
        )
        return qs

    def unbalanced_transactions(self):
        return self.with_balances().exclude(balances_debit=models.F("balances_credit"))


class TransactionManager(models.Manager):
    def get_queryset(self):
        return TransactionQuerySet(self.model, using=self._db)

    def with_balances(self):
        return self.get_queryset().with_balances()

    def unbalanced_transactions(self):
        return self.get_queryset().unbalanced_transactions()

    @log_call(".created")
    def create(self, *args, **kwargs):
        return super().create(*args, **kwargs)


class Transaction(models.Model, LogTargetMixin):
    objects = TransactionManager()

    LOG_TARGET_BASE = "byro.bookkeeping.transaction"

    memo = models.CharField(max_length=1000, null=True)
    booking_datetime = models.DateTimeField(null=True)
    value_datetime = models.DateTimeField()
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        to=get_user_model(),
        on_delete=models.PROTECT,
        related_name="+",  # no related lookup
        null=True,
    )

    reverses = models.ForeignKey(
        to="Transaction",
        on_delete=models.PROTECT,
        related_name="reversed_by",
        null=True,
    )

    data = JSONField(null=True)

    documents = models.ManyToManyField(Document, through="DocumentTransactionLink")

    @log_call(".debit.created", log_on="self")
    def debit(self, account, *args, **kwargs):
        return Booking.objects.create(
            transaction=self, debit_account=account, *args, **kwargs
        )

    @log_call(".credit.created", log_on="self")
    def credit(self, account, *args, **kwargs):
        return Booking.objects.create(
            transaction=self, credit_account=account, *args, **kwargs
        )

    @transaction.atomic
    def reverse(self, value_datetime=None, *args, **kwargs):
        if "user_or_context" not in kwargs:
            raise TypeError(
                "You need to provide a 'user_or_context' named parameter which indicates the responsible user (a User model object), request (a View instance or HttpRequest object), or generic context (a str)."
            )
        user_or_context = kwargs.pop("user_or_context")
        user = kwargs.pop("user", None)

        t = Transaction.objects.create(
            value_datetime=value_datetime or self.value_datetime,
            reverses=self,
            user_or_context=user_or_context,
            user=user,
            *args,
            **kwargs,
        )
        for b in self.bookings.all():
            if b.credit_account:
                t.debit(
                    account=b.credit_account,
                    amount=b.amount,
                    member=b.member,
                    user_or_context=user_or_context,
                    user=user,
                )
            elif b.debit_account:
                t.credit(
                    account=b.debit_account,
                    amount=b.amount,
                    member=b.member,
                    user_or_context=user_or_context,
                    user=user,
                )
        t.save()
        self.log(user_or_context, ".reversed", user=user, reversed_by=t)

        return t

    @property
    def debits(self):
        return self.bookings.exclude(debit_account=None)

    @property
    def credits(self):
        return self.bookings.exclude(credit_account=None)

    @property
    def balances(self):
        balances = {
            "debit": self.debits.aggregate(total=models.Sum("amount"))["total"] or 0,
            "credit": self.credits.aggregate(total=models.Sum("amount"))["total"] or 0,
        }
        return balances

    @property
    def is_read_only(self):
        "Advisory property: don't modify this Transaction or its Bookings"
        # Future proof: For now, don't modify balanced transactions
        return self.is_balanced

    @property
    def is_balanced(self):
        if hasattr(self, "balances_debit"):
            return self.balances_debit == self.balances_credit
        else:
            balances = self.balances
            return balances["debit"] == balances["credit"]

    def find_memo(self):
        if self.memo:
            return self.memo

        if hasattr(self, "cached_bookings"):
            for booking in self.cached_bookings:
                if booking.memo:
                    return booking.memo

        booking = self.bookings.exclude(memo=None).first()
        if booking:
            return booking.memo

        return None

    @transaction.atomic
    def process_transaction(self):
        """
        Collects responses to the signal `process_transaction`.
        Re-raises received Exceptions.

        Returns the number of receivers that augmented the Transaction.
        """
        from byro.bookkeeping.signals import process_transaction

        response_counter = Counter()
        this_counter = Counter("dummy")

        while (
            not response_counter or response_counter.most_common(1)[0][1] < 5
        ) and sum(this_counter.values()) > 0:
            responses = process_transaction.send_robust(sender=self)
            this_counter = Counter(
                receiver for receiver, response in responses if response
            )

            for receiver, response in responses:
                if isinstance(response, Exception):
                    raise response

            response_counter += this_counter

        if sum(response_counter.values()) < 1:
            raise Exception("No plugin tried to augment the transaction.")

        response_counter += Counter()  # Remove zero and negative elements
        return len(response_counter)

    def __str__(self):
        return "Transaction(pk={}, memo={!r}, value_datetime={!r}{})".format(
            self.pk,
            self.find_memo(),
            self.value_datetime.isoformat(),
            ", reverses={}".format(self.reverses) if self.reverses else "",
        )

    def get_absolute_url(self):
        return reverse("office:finance.transactions.detail", kwargs={"pk": self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-money"></i> ')


class DocumentTransactionLink(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)


class BookingsQuerySet(models.QuerySet):
    def with_transaction_balances(self):
        qs = self.annotate(
            transaction_balances_debit=models.Sum(
                models.Case(
                    models.When(
                        ~models.Q(transaction__bookings__debit_account=None),
                        then="transaction__bookings__amount",
                    ),
                    default=0,
                    output_field=models.DecimalField(max_digits=8, decimal_places=2),
                )
            ),
            transaction_balances_credit=models.Sum(
                models.Case(
                    models.When(
                        ~models.Q(transaction__bookings__credit_account=None),
                        then="transaction__bookings__amount",
                    ),
                    default=0,
                    output_field=models.DecimalField(max_digits=8, decimal_places=2),
                )
            ),
        )
        return qs

    def with_transaction_data(self):
        qs = self.with_transaction_balances()
        qs = qs.select_related(
            "member", "transaction", "credit_account", "debit_account"
        )
        qs = qs.prefetch_related(
            Prefetch("transaction__bookings", to_attr="cached_bookings"),
            "transaction__cached_bookings__credit_account",
            "transaction__cached_bookings__debit_account",
            "transaction__cached_bookings__member",
        )
        return qs


class Booking(models.Model):
    objects = BookingsQuerySet.as_manager()

    memo = models.CharField(max_length=1000, null=True)

    booking_datetime = models.DateTimeField(null=True)
    modified = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        to=get_user_model(),
        on_delete=models.PROTECT,
        related_name="+",  # no related lookup
        null=True,
    )

    transaction = models.ForeignKey(
        to="Transaction", related_name="bookings", on_delete=models.PROTECT
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    debit_account = models.ForeignKey(
        to="bookkeeping.Account",
        related_name="debits",
        on_delete=models.PROTECT,
        null=True,
    )
    credit_account = models.ForeignKey(
        to="bookkeeping.Account",
        related_name="credits",
        on_delete=models.PROTECT,
        null=True,
    )
    member = models.ForeignKey(
        to="members.Member",
        related_name="bookings",
        on_delete=models.PROTECT,
        null=True,
    )

    importer = models.CharField(null=True, max_length=500)
    data = JSONField(null=True)
    source = models.ForeignKey(
        to="bookkeeping.RealTransactionSource",
        on_delete=models.SET_NULL,
        related_name="bookings",
        null=True,
    )

    def __str__(self):
        return "{booking_type} {account} {amount} {memo}".format(
            booking_type="debit" if self.debit_account else "credit",
            account=self.debit_account or self.credit_account,
            amount=self.amount,
            memo=self.memo,
        )

    class Meta:
        # This is defense in depth, per django-db-constraints module.
        # FUTURE: Should also add a signal or save handler for the same
        #   constraint in pure python
        db_constraints = {
            "exactly_either_debit_or_credit": "CHECK (NOT ((debit_account_id IS NULL) = (credit_account_id IS NULL)))"
        }

    def find_memo(self):
        if self.memo:
            return self.memo
        return self.transaction.find_memo()

    @property
    def counter_bookings(self):
        if hasattr(self.transaction, "cached_bookings"):
            # Was prefetched with with_transaction_data()
            if self.debit_account:
                return [b for b in self.transaction.cached_bookings if b.credit_account]
            elif self.credit_account:
                return [b for b in self.transaction.cached_bookings if b.debit_account]
        else:
            if self.debit_account:
                return self.transaction.credits
            elif self.credit_account:
                return self.transaction.debits
        return None
