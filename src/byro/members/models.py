from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db import models
from django.db.models.fields.related import OneToOneRel
from django.utils.decorators import classproperty
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from byro.common.models.auditable import Auditable
from byro.common.models.configuration import Configuration
from byro.common.models.choices import Choices


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

    @property
    def balance(self) -> Decimal:
        config = Configuration.get_solo()
        cutoff = now() - relativedelta(months=config.liability_interval)
        qs = self.transactions.filter(value_datetime__lte=now(), value_datetime__gte=cutoff)
        liability = qs.filter(source_account__account_category='member_fees').aggregate(liability=models.Sum('amount'))['liability'] or Decimal('0.00')
        asset = qs.filter(destination_account__account_category='member_fees').aggregate(asset=models.Sum('amount'))['asset'] or Decimal('0.00')
        return asset - liability

    @property
    def donations(self):
        return self.transactions.filter(value_datetime__lte=now()).filter(
            destination_account__account_category='member_donation'
        )

    @property
    def fee_payments(self):
        return self.transactions.filter(value_datetime__lte=now()).filter(
            destination_account__account_category='member_fees'
        )

    def update_liabilites(self):
        from byro.bookkeeping.models import Account, VirtualTransaction

        config = Configuration.get_solo()
        booking_date = now()
        cutoff = (booking_date - relativedelta(months=config.liability_interval)).date()
        account = Account.objects.filter(account_category='member_fees').first()

        for membership in self.memberships.all():
            date = membership.start
            if date < cutoff:
                date = cutoff
            end = membership.end or booking_date.date()
            while date <= end:
                vt = VirtualTransaction.objects.filter(
                    source_account=account,
                    value_datetime=date,
                    member=self,
                ).first()

                if vt:
                    if vt.amount != membership.amount:
                        vt.amount = membership.amount
                        vt.save()
                else:
                    VirtualTransaction.objects.create(
                        source_account=account,
                        value_datetime=date,
                        amount=membership.amount,
                        member=self,
                    )
                date += relativedelta(months=membership.interval)

    def remove_future_liabilites_on_leave(self):
        for vt in self.transactions.all():
            delete_vt = True
            for membership in self.memberships.all():
                if vt.value_datetime.date() < membership.end:
                    delete_vt = False
            if delete_vt and not vt.real_transaction:
                vt.delete()

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
