from collections import OrderedDict
from decimal import Decimal
from functools import reduce

from dateutil.relativedelta import relativedelta
from django.db import models, transaction
from django.db.models import Q
from django.db.models.fields.related import OneToOneRel
from django.urls import reverse
from django.utils.decorators import classproperty
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from byro.bookkeeping.models import Booking, Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.common.models import Configuration, LogEntry, LogTargetMixin
from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices


class Field:
    field_id = str
    name = str
    description = str

    computed = bool
    read_only = bool
    registration_form = dict

    def __init__(
        self, field_id, name, description, path, registration_form=None, **kwargs
    ):
        self.field_id = field_id
        self.name = name
        self.description = description
        self.path = path
        self.registration_form = registration_form or {}
        for k, v in kwargs.items():
            setattr(self, k, v)

    @staticmethod
    def _follow_path(start, path):
        """Follow a python.dot.path until its penultimate item, then return the current object and the name of the last descriptor.
        Allows 'func()' syntax to call a method along the way without arguments.

        Examples:
            _follow_path(m, 'pk')  ->  m, 'pk'
            _follow_path(m, 'profile_foo.bar')  ->  m.profile_foo, 'bar'
            _follow_path(m, 'memberships.last().start')  ->  m.memberships.last(), 'start'
        """
        target = start
        path = path.split(".")
        for p in path[:-1]:
            target = getattr(target, p.rsplit("(")[0], None)
            if p.endswith("()") and target is not None:
                target = target()
        return target, path[-1]

    def getter(self, member):
        target, prop = self._follow_path(member, self.path)
        return getattr(target, prop, None)

    def setter(self, member, value):
        if self.read_only:
            raise NotImplementedError(
                "Writing to {} is not supported".format(self.path)
            )
        target, prop = self._follow_path(member, self.path)
        if target is None:
            raise AttributeError(
                "Encountered 'None' while following {}".format(self.path)
            )
        setattr(target, prop, value)
        if callable(getattr(target, "save", None)):
            target.save()


class MemberTypes:
    MEMBER = "member"
    EXTERNAL = "external"


class MemberContactTypes(Choices):
    ORGANIZATION = "organization"
    PERSON = "person"
    ROLE = "role"


class MemberQuerySet(models.QuerySet):
    def with_active_membership(self):
        return (
            self.filter(
                Q(memberships__start__lte=now().date())
                & (
                    Q(memberships__end__isnull=True)
                    | Q(memberships__end__gte=now().date())
                )
            )
            .order_by("-id")
            .distinct()
        )


class MemberManager(models.Manager):
    def get_queryset(self):
        return MemberQuerySet(self.model, using=self._db).filter(
            membership_type=MemberTypes.MEMBER
        )

    def with_active_membership(self):
        return self.get_queryset().with_active_membership()


class AllMemberManager(models.Manager):
    pass


def get_next_member_number():
    all_numbers = Member.all_objects.all().values_list("number", flat=True)
    numeric_numbers = [n for n in all_numbers if n is not None and n.isdigit()]
    try:
        return max(int(n) for n in numeric_numbers) + 1
    except Exception:
        return 1


def get_member_data(obj):
    if hasattr(obj, "get_member_data"):
        return obj.get_member_data()
    return [
        (field.verbose_name, str(getattr(obj, field.name)))
        for field in obj._meta.fields
        if field.name
        not in ("id", "created_by", "modified_by", "created", "modified", "member")
    ]


class Member(Auditable, models.Model, LogTargetMixin):
    LOG_TARGET_BASE = "byro.members"

    number = models.CharField(
        max_length=100,
        verbose_name=_("Membership number/ID"),
        null=True,
        blank=True,
        db_index=True,
    )
    name = models.CharField(
        max_length=100, verbose_name=_("Name"), null=True, blank=True
    )
    address = models.TextField(
        max_length=300, verbose_name=_("Address"), null=True, blank=True
    )
    email = models.EmailField(
        max_length=200, verbose_name=_("E-Mail"), null=True, blank=True
    )
    membership_type = models.CharField(max_length=40, default=MemberTypes.MEMBER)
    member_contact_type = models.CharField(
        max_length=MemberContactTypes.max_length,
        verbose_name=_("Contact type"),
        choices=MemberContactTypes.choices,
        default=MemberContactTypes.PERSON,
    )

    form_title = _("Member")
    objects = MemberManager()
    all_objects = AllMemberManager()

    @classproperty
    def profile_classes(cls) -> list:
        return [
            related.related_model
            for related in cls._meta.related_objects
            if isinstance(related, OneToOneRel) and related.name.startswith("profile_")
        ]

    @property
    def profiles(self) -> list:
        return [
            getattr(self, related.name)
            for related in self._meta.related_objects
            if isinstance(related, OneToOneRel) and related.name.startswith("profile_")
        ]

    @classmethod
    def get_fields(cls):
        result = []

        result.append(
            Field(
                "_internal_id",
                _("Internal database ID"),
                "",
                "pk",
                computed=True,
                read_only=True,
            )
        )
        result.append(
            Field(
                "_internal_active",
                _("Member active?"),
                "",
                "is_active",
                computed=True,
                read_only=True,
            )
        )
        result.append(
            Field(
                "_internal_balance",
                _("Account balance"),
                "",
                "balance",
                computed=True,
                read_only=True,
            )
        )

        reg_form = Configuration.get_solo().registration_form or []
        form_config = {entry["name"]: entry for entry in reg_form}

        profile_map = {
            profile.related_model: profile.name
            for profile in cls._meta.related_objects
            if isinstance(profile, OneToOneRel) and profile.name.startswith("profile_")
        }

        for model in [cls, Membership] + cls.profile_classes:
            for field in model._meta.fields:
                if field.name in ("id", "member") or (
                    model is Member and field.name == "membership_type"
                ):
                    continue

                f_id = "{}__{}".format(
                    SPECIAL_NAMES.get(model, model.__name__), field.name
                )
                f_name = field.verbose_name or field.name

                if issubclass(model, cls):
                    f_path = field.name
                elif model is Membership:
                    f_path = "memberships.last().{}".format(field.name)
                    f_name = "{} ({})".format(f_name, _("Current membership"))
                else:
                    f_path = "{}.{}".format(profile_map[model], field.name)
                    f_name = "{} ({})".format(f_name, model.__name__)

                result.append(
                    Field(
                        f_id,
                        f_name,
                        "",
                        f_path,
                        registration_form=form_config.get(f_id, None),
                        computed=False,
                        read_only=False,
                    )
                )

        return OrderedDict([(f.field_id, f) for f in result])

    def _calc_balance(
        self,
        liability_cutoff=None,
        asset_cutoff=None,
        liability_start=None,
        asset_start=None,
    ) -> Decimal:
        _now = now()
        fees_receivable_account = SpecialAccounts.fees_receivable
        qs = Booking.objects.filter(member=self)
        debits = qs.filter(
            debit_account=fees_receivable_account,
            transaction__value_datetime__lte=liability_cutoff or _now,
        )
        if liability_start:
            debits = debits.filter(transaction__value_datetime__gte=liability_start)
        credits = qs.filter(
            credit_account=fees_receivable_account,
            transaction__value_datetime__lte=asset_cutoff or _now,
        )
        if asset_start:
            credits = credits.filter(transaction__value_datetime__gte=asset_start)
        liability = debits.aggregate(liability=models.Sum("amount"))[
            "liability"
        ] or Decimal("0.00")
        asset = credits.aggregate(asset=models.Sum("amount"))["asset"] or Decimal(
            "0.00"
        )
        return asset - liability

    @property
    def balance(self) -> Decimal:
        return self._calc_balance()

    def create_balance(self, start, end, commit=True, create_if_zero=True):
        if self.balances.exists():
            if self.balances.filter(
                models.Q(
                    models.Q(start__lte=start) & models.Q(end__gte=start)
                )  # start overlaps
                | models.Q(
                    models.Q(start__lte=end) & models.Q(end__gte=end)
                )  # end overlaps
            ).exists():
                raise Exception(
                    "Cannot create overlapping balance: {} from {} to {}".format(
                        self, start, end
                    )
                )
        amount = self._calc_balance(
            liability_cutoff=end,
            asset_cutoff=end,
            liability_start=start,
            asset_start=start,
        )
        if not amount and not create_if_zero:
            return
        balance = MemberBalance(member=self, start=start, end=end, amount=amount)
        if commit is True:
            balance.save()
        return balance

    def statute_barred_debt(self, future_limit=relativedelta()) -> Decimal:
        limit = (
            relativedelta(months=Configuration.get_solo().liability_interval)
            - future_limit
        )
        last_unenforceable_date = (
            now().replace(month=12, day=31) - limit - relativedelta(years=1)
        )
        return max(Decimal("0.00"), -self._calc_balance(last_unenforceable_date))

    @property
    def donation_balance(self) -> Decimal:
        return self.donations.aggregate(donations=models.Sum("amount"))[
            "donations"
        ] or Decimal("0.00")

    @property
    def donations(self):
        return Booking.objects.filter(
            credit_account=SpecialAccounts.donations,
            member=self,
            transaction__value_datetime__lte=now(),
        )

    @property
    def fee_payments(self):
        return Booking.objects.filter(
            debit_account=SpecialAccounts.fees_receivable,
            member=self,
            transaction__value_datetime__lte=now(),
        )

    @property
    def is_active(self):
        if not self.memberships.count():
            return False
        result = self.memberships.last().start <= now().date()
        if self.memberships.last().end:
            result = result and not (self.memberships.last().end < now().date())
        return result

    @property
    def record_disclosure_email(self):
        config = Configuration.get_solo()
        template = config.record_disclosure_template
        data = get_member_data(self)
        for profile in self.profiles:
            data += get_member_data(profile)
        key_value_data = [d for d in data if len(d) == 2 and not isinstance(d, str)]
        text_data = [d for d in data if isinstance(d, str)]
        key_length = min(max(len(d[0]) for d in key_value_data), 20)
        key_value_text = []
        for key, value in key_value_data:
            key = (key + ":").ljust(key_length) + " "
            value = value.strip()
            if value in [None, "None", ""]:
                value = "-"
            if isinstance(value, str) and "\n" in value:
                value = "\n".join(
                    [" " * (key_length + 1) + line for line in value.split("\n")]
                ).strip()
            key_value_text.append(key + value)
        key_value_text = "\n".join(key_value_text)
        if text_data:
            key_value_text += "\n" + "\n".join(text_data)
        context = {
            "association_name": config.name,
            "data": key_value_text,
            "number": self.number,
            "balance": "{currency} {balance}".format(
                currency=config.currency, balance=self.balance
            ),
        }
        return template.to_mail(self.email, context=context, save=False)

    @transaction.atomic
    def update_liabilites(self):
        src_account = SpecialAccounts.fees
        dst_account = SpecialAccounts.fees_receivable

        # Step 1: Identify all dates and amounts that should be due at those dates
        #  (in python, store as a list; hits database once to get list of memberships)
        # Step 2: Find all due amounts within the data ranges, ignore reversed liabilities
        #  (hits database)
        # Step 3: Compare due date and amounts with list from step 1
        #  (in Python)
        # Step 4: Cancel all liabilities that didn't match in step 3
        #  (hits database, once per mismatch)
        # Step 5: Add all missing liabilities
        #  (hits database, once per new due)
        # Step 6: Find and cancel all liabilities outside of membership dates, replaces remove_future_liabilites_on_leave()
        #  (hits database, once for search, once per stray liability)

        dues = set()
        membership_ranges = []
        _now = now()

        # Step 1
        for membership in self.memberships.all():
            if not membership.amount:
                continue
            membership_range, membership_dues = membership.get_dues(_now=_now)
            membership_ranges.append(membership_range)
            dues |= membership_dues

        # Step 2
        dues_qs = Booking.objects.filter(
            member=self,
            credit_account=src_account,
            transaction__reversed_by__isnull=True,
        )
        if membership_ranges:
            date_range_q = reduce(
                lambda a, b: a | b,
                [
                    models.Q(transaction__value_datetime__gte=start)
                    & models.Q(transaction__value_datetime__lte=end)
                    for start, end in membership_ranges
                ],
            )
            dues_qs = dues_qs.filter(date_range_q)
        dues_in_db = {  # Must be a dictionary instead of set, to retrieve b later on
            (b.transaction.value_datetime.date(), b.amount): b for b in dues_qs.all()
        }

        # Step 3
        dues_in_db_as_set = set(dues_in_db.keys())
        wrong_dues_in_db = dues_in_db_as_set - dues
        missing_dues = dues - dues_in_db_as_set

        # Step 4
        for wrong_due in sorted(wrong_dues_in_db):
            booking = dues_in_db[wrong_due]
            booking.transaction.reverse(
                memo=_("Due amount canceled because of change in membership amount"),
                user_or_context="internal: update_liabilites, membership amount changed",
            )

        # Step 5:
        for (date, amount) in sorted(missing_dues):
            t = Transaction.objects.create(
                value_datetime=date,
                booking_datetime=_now,
                memo=_("Membership due"),
                user_or_context="internal: update_liabilites, add missing liabilities",
            )
            t.credit(
                account=src_account,
                amount=amount,
                member=self,
                user_or_context="internal: update_liabilites, add missing liabilities",
            )
            t.debit(
                account=dst_account,
                amount=amount,
                member=self,
                user_or_context="internal: update_liabilites, add missing liabilities",
            )
            t.save()

        # Step 6:
        stray_liabilities_qs = Booking.objects.filter(
            member=self,
            credit_account=src_account,
            transaction__reversed_by__isnull=True,
        )
        if membership_ranges:
            stray_liabilities_qs = stray_liabilities_qs.exclude(date_range_q)
        stray_liabilities_qs = stray_liabilities_qs.prefetch_related("transaction")
        for stray_liability in stray_liabilities_qs.all():
            stray_liability.transaction.reverse(
                memo=_("Due amount outside of membership canceled"),
                user_or_context="internal: update_liabilites, reverse stray liabilities",
            )

    def __str__(self):
        return "Member {self.number} ({self.name})".format(self=self)

    def get_absolute_url(self):
        return reverse("office:members.data", kwargs={"pk": self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-user"></i> ')

    def log_entries(self):
        own_entries = [e.pk for e in super().log_entries()]
        ms_entries = [e.pk for m in self.memberships.all() for e in m.log_entries()]
        return LogEntry.objects.filter(pk__in=own_entries + ms_entries)


class FeeIntervals:
    MONTHLY = 1
    QUARTERLY = 3
    BIANNUAL = 6
    ANNUALLY = 12

    @classproperty
    def choices(cls):
        return (
            (cls.MONTHLY, _("monthly")),
            (cls.QUARTERLY, _("quarterly")),
            (cls.BIANNUAL, _("biannually")),
            (cls.ANNUALLY, _("annually")),
        )


class MembershipType(Auditable, models.Model):
    name = models.CharField(max_length=200, verbose_name=_("name"))
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("amount"),
        help_text=_("Please enter the yearly fee for this membership type."),
    )


class Membership(Auditable, models.Model, LogTargetMixin):
    LOG_TARGET_BASE = "byro.members.membership"

    member = models.ForeignKey(
        to="members.Member", on_delete=models.CASCADE, related_name="memberships"
    )
    start = models.DateField(verbose_name=_("start"))
    end = models.DateField(verbose_name=_("end"), null=True, blank=True)
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name=_("membership fee"),
        help_text=_("The amount to be paid in the chosen interval"),
    )
    interval = models.IntegerField(
        choices=FeeIntervals.choices,
        verbose_name=_("payment interval"),
        help_text=_("How often does the member pay their fees?"),
    )

    form_title = _("Membership")

    def get_absolute_url(self):
        return reverse("office:members.data", kwargs={"pk": self.member.pk})

    def get_dues(self, _now=None):
        _now = _now or now()
        dues = set()
        end = self.end
        if not end:
            try:
                end = _now.replace(day=self.start.day).date()
            except ValueError:  # membership.start.day is not a valid date in our month, we'll use the last date instead
                end = (_now + relativedelta(day=1, months=1, days=-1)).date()
        date = self.start
        while date <= end:
            dues.add((date, self.amount))
            date += relativedelta(months=self.interval)
        return (self.start, end), dues


SPECIAL_NAMES = {Member: "member", Membership: "membership"}

SPECIAL_ORDER = [
    "member__number",
    "member__name",
    "member__address",
    "member__email",
    "membership__start",
    "membership__interval",
    "membership__amount",
]


class MemberBalance(models.Model):
    """
    Member balance entries are similar in nature to invoices, describing the
    amount owed over a certain period in time.

    As they MUST NOT overlap per member, they should be created via the
    ``Member.create_balance(start, end)`` method interface.
    """

    member = models.ForeignKey(
        to="members.Member", related_name="balances", on_delete=models.PROTECT
    )
    reference = models.CharField(
        null=True,
        blank=True,
        verbose_name=_("Reference"),
        help_text=_("For example an invoice number or a payment reference"),
        unique=True,
        max_length=50,
    )
    amount = models.DecimalField(
        max_digits=8, decimal_places=2, verbose_name=_("Amount")
    )
    start = models.DateTimeField(verbose_name=_("Start"))
    end = models.DateTimeField(verbose_name=_("End"))
    state = models.CharField(
        choices=[
            ("paid", _("paid")),
            ("partial", _("partially paid")),
            ("unpaid", _("unpaid")),
        ],
        default="unpaid",
        max_length=7,
    )
