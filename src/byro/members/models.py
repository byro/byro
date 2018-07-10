from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models.fields.related import OneToOneRel
from django.utils.decorators import classproperty
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from byro.bookkeeping.models import Booking, Transaction
from byro.bookkeeping.special_accounts import SpecialAccounts
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


class Member(Auditable, models.Model):

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
        if amount >=0:
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

    def update_liabilites(self):
        src_account = SpecialAccounts.fees
        dst_account = SpecialAccounts.fees_receivable

        for membership in self.memberships.all():
            booking_date = now().replace(day=membership.start.day)
            date = membership.start
            end = membership.end or booking_date.date()
            transactions_by_date = {
                t.value_datetime.date(): t
                for t in Transaction.objects.with_balances().filter(
                    value_datetime__gte=date,
                    value_datetime__lte=end,
                    bookings__credit_account=src_account,
                    bookings__member=self,
                ).prefetch_related('bookings').all()
            }
            while date <= end:
                t = transactions_by_date.get(date, None)

                if t:
                    if t.balances_credit != membership.amount:
                        if not t.reversed_by.count():
                            # Cancel transaction, create a new one
                            t.reverse(memo=_('Due amount canceled because of change in membership amount'))
                        t = False

                if not t:
                    t = Transaction.objects.create(value_datetime=date, memo=_("Membership due"), booking_datetime=booking_date)
                    t.credit(account=src_account, amount=membership.amount, member=self)
                    t.debit(account=dst_account, amount=membership.amount, member=self)
                    t.save()

                date += relativedelta(months=membership.interval)

    def remove_future_liabilites_on_leave(self):
        for t in Transaction.objects.filter(bookings__debit_account=SpecialAccounts.fees_receivable, bookings__member=self):
            do_delete = True
            for membership in self.memberships.all():
                if t.value_datetime.date() < membership.end:
                    do_delete = False
            if do_delete and not t.reversed_by.count():
                t.reverse(memo=_("Due amount canceled on leave"))

    def __str__(self):
        return 'Member {self.number} ({self.name})'.format(self=self)


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


class Membership(Auditable, models.Model):
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
