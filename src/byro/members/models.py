from datetime import timedelta
from decimal import Decimal
from functools import reduce

from dateutil.relativedelta import relativedelta
from django.db import models, transaction
from django.db.models.fields.related import OneToOneRel
from django.urls import reverse
from django.utils.decorators import classproperty
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from byro.bookkeeping.models import Booking, Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.common.models import LogEntry, LogTargetMixin
from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices
from byro.common.models.configuration import Configuration


class MemberTypes:
    MEMBER = 'member'
    EXTERNAL = 'external'


class MemberContactTypes(Choices):
    ORGANIZATION = 'organization'
    PERSON = 'person'
    ROLE = 'role'


class MemberManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(membership_type=MemberTypes.MEMBER)


class AllMemberManager(models.Manager):
    pass


def get_next_member_number():
    all_numbers = Member.all_objects.all().values_list('number', flat=True)
    numeric_numbers = [n for n in all_numbers if n is not None and n.isdigit()]
    try:
        return max(int(n) for n in numeric_numbers) + 1
    except Exception:
        return 1


def get_member_data(obj):
    if hasattr(obj, 'get_member_data'):
        return obj.get_member_data()
    return [
        (field.verbose_name, str(getattr(obj, field.name)))
        for field in obj._meta.fields
        if field.name not in ('id', 'created_by', 'modified_by', 'created', 'modified', 'member')
    ]


class Member(Auditable, models.Model, LogTargetMixin):
    LOG_TARGET_BASE = 'byro.members'

    number = models.CharField(
        max_length=100,
        verbose_name=_('Membership number/ID'),
        null=True, blank=True,
        db_index=True,
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Name'),
        null=True, blank=True,
    )
    address = models.TextField(
        max_length=300,
        verbose_name=_('Address'),
        null=True, blank=True,
    )
    email = models.EmailField(
        max_length=200,
        verbose_name=_('E-Mail'),
        null=True, blank=True,
    )
    membership_type = models.CharField(
        max_length=40,
        default=MemberTypes.MEMBER,
    )
    member_contact_type = models.CharField(
        max_length=MemberContactTypes.max_length,
        verbose_name=_('Contact type'),
        choices=MemberContactTypes.choices,
        default=MemberContactTypes.PERSON,
    )

    form_title = _('Member')
    objects = MemberManager()
    all_objects = AllMemberManager()

    @classproperty
    def profile_classes(cls) -> list:
        return [
            related.related_model for related in cls._meta.related_objects
            if isinstance(related, OneToOneRel) and related.name.startswith('profile_')
        ]

    @property
    def profiles(self) -> list:
        return [
            getattr(self, related.name)
            for related in self._meta.related_objects
            if isinstance(related, OneToOneRel) and related.name.startswith('profile_')
        ]

    def _calc_balance(self, liability_cutoff=None, asset_cutoff=None) -> Decimal:
        _now = now()
        fees_receivable_account = SpecialAccounts.fees_receivable
        debits = Booking.objects.filter(debit_account=fees_receivable_account, member=self, transaction__value_datetime__lte=liability_cutoff or _now)
        credits = Booking.objects.filter(credit_account=fees_receivable_account, member=self, transaction__value_datetime__lte=asset_cutoff or _now)
        liability = debits.aggregate(liability=models.Sum('amount'))['liability'] or Decimal('0.00')
        asset = credits.aggregate(asset=models.Sum('amount'))['asset'] or Decimal('0.00')
        return asset - liability

    @property
    def balance(self) -> Decimal:
        return self._calc_balance()

    def waive_debts_before_date(self, date):
        cutoff_date = date - timedelta(days=1)
        amount = self._calc_balance(cutoff_date, cutoff_date)
        if amount >= 0:
            return
        amount = abs(amount)
        src_account = SpecialAccounts.fees_receivable
        dst_account = SpecialAccounts.fees
        t = Transaction.objects.create(value_datetime=date, memo=_("Membership debts waived"), booking_datetime=now())
        t.credit(account=src_account, amount=amount, member=self)
        t.debit(account=dst_account, amount=amount, member=self)
        t.save()
        return amount

    def statute_barred_debt(self, future_limit=relativedelta()) -> Decimal:
        limit = relativedelta(months=Configuration.get_solo().liability_interval) - future_limit
        last_unenforceable_date = now().replace(month=12, day=31) - limit - relativedelta(years=1)
        return max(Decimal('0.00'), -self._calc_balance(last_unenforceable_date))

    @property
    def donation_balance(self) -> Decimal:
        return self.donations.aggregate(donations=models.Sum('amount'))['donations'] or Decimal('0.00')

    @property
    def donations(self):
        return Booking.objects.filter(credit_account=SpecialAccounts.donations, member=self, transaction__value_datetime__lte=now())

    @property
    def fee_payments(self):
        return Booking.objects.filter(debit_account=SpecialAccounts.fees_receivable, member=self, transaction__value_datetime__lte=now())

    @property
    def is_active(self):
        if not self.memberships.count():
            return False
        result = (self.memberships.last().start <= now().date())
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
        key_value_text = '\n'.join((key + ':').ljust(key_length) + ' ' + value for key, value in key_value_data)
        if text_data:
            key_value_text += '\n' + '\n'.join(text_data)
        context = {
            'association_name': config.name,
            'data': key_value_text,
            'number': self.number,
            'balance': '{currency} {balance}'.format(currency=config.currency, balance=self.balance)
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
            booking_date = _now.replace(day=membership.start.day)
            date = membership.start
            end = membership.end or booking_date.date()
            membership_ranges.append((date, end))
            while date <= end:
                dues.add((date, membership.amount))
                date += relativedelta(months=membership.interval)

        # Step 2
        date_range_q = reduce(
            lambda a, b: a | b, [
                models.Q(transaction__value_datetime__gte=start) & models.Q(transaction__value_datetime__lte=end)
                for start, end in membership_ranges
            ]
        )
        dues_qs = Booking.objects.filter(
            member=self,
            credit_account=src_account,
            transaction__reversed_by__isnull=True,
        ).filter(date_range_q)
        dues_in_db = {  # Must be a dictionary instead of set, to retrieve b later on
            (b.transaction.value_datetime.date(), b.amount): b
            for b in dues_qs.all()
        }

        # Step 3
        dues_in_db_as_set = set(dues_in_db.keys())
        wrong_dues_in_db = dues_in_db_as_set - dues
        missing_dues = dues - dues_in_db_as_set

        # Step 4
        for wrong_due in sorted(wrong_dues_in_db):
            booking = dues_in_db[wrong_due]
            booking.transaction.reverse(memo=_('Due amount canceled because of change in membership amount'), user_or_context='internal: update_liabilites, membership amount changed',)

        # Step 5:
        for (date, amount) in sorted(missing_dues):
            t = Transaction.objects.create(
                value_datetime=date,
                booking_datetime=_now,
                memo=_("Membership due"),
                user_or_context='internal: update_liabilites, add missing liabilities',
            )
            t.credit(account=src_account, amount=amount, member=self, user_or_context='internal: update_liabilites, add missing liabilities')
            t.debit(account=dst_account, amount=amount, member=self, user_or_context='internal: update_liabilites, add missing liabilities',)
            t.save()

        # Step 6:
        stray_liabilities_qs = Booking.objects.filter(
            member=self,
            credit_account=src_account,
            transaction__reversed_by__isnull=True,
        ).exclude(date_range_q).prefetch_related('transaction')
        for stray_liability in stray_liabilities_qs.all():
            stray_liability.transaction.reverse(memo=_("Due amount outside of membership canceled"), user_or_context='internal: update_liabilites, reverse stray liabilities',)

    def __str__(self):
        return 'Member {self.number} ({self.name})'.format(self=self)

    def get_absolute_url(self):
        return reverse('office:members.data', kwargs={'pk': self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-user"></i> ')

    def log_entries(self):
        own_entries = [e.pk for e in super().log_entries()]
        ms_entries = [e.pk for m in self.memberships.all() for e in m.log_entries()]
        return LogEntry.objects.filter(pk__in=own_entries+ms_entries)


class FeeIntervals:
    MONTHLY = 1
    QUARTERLY = 3
    BIANNUAL = 6
    ANNUALLY = 12

    @classproperty
    def choices(cls):
        return (
            (cls.MONTHLY, _('monthly')),
            (cls.QUARTERLY, _('quarterly')),
            (cls.BIANNUAL, _('biannually')),
            (cls.ANNUALLY, _('annually')),
        )


class MembershipType(Auditable, models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name=_('name'),
    )
    amount = models.DecimalField(
        max_digits=8, decimal_places=2,
        verbose_name=_('amount'),
        help_text=_('Please enter the yearly fee for this membership type.')
    )


class Membership(Auditable, models.Model, LogTargetMixin):
    LOG_TARGET_BASE = 'byro.members.membership'

    member = models.ForeignKey(
        to='members.Member',
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    start = models.DateField(
        verbose_name=_('start'),
    )
    end = models.DateField(
        verbose_name=_('end'),
        null=True, blank=True,
    )
    amount = models.DecimalField(
        max_digits=8, decimal_places=2,
        verbose_name=_('membership fee'),
        help_text=_('The amount to be paid in the chosen interval'),
    )
    interval = models.IntegerField(
        choices=FeeIntervals.choices,
        verbose_name=_('payment interval'),
        help_text=_('How often does the member pay their fees?'),
    )

    form_title = _('Membership')

    def get_absolute_url(self):
        return reverse('office:members.data', kwargs={'pk': self.member.pk})
