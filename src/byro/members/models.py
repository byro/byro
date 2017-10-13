from django.db import models
from django.db.models.fields.related import OneToOneRel
from django.utils.decorators import classproperty
from django.utils.translation import ugettext_lazy as _

from byro.common.models.auditable import Auditable


class Member(Auditable, models.Model):

    number = models.CharField(
        max_length=100,
        null=True, blank=True,
    )
    name = models.CharField(
        max_length=100,
        null=True, blank=True,
    )
    address = models.TextField(
        max_length=300,
        null=True, blank=True,
    )
    email = models.EmailField(
        max_length=200,
        null=True, blank=True,
    )

    @property
    def profiles(self) -> list:
        profiles = []

        for related in self._meta.related_objects:
            if not isinstance(related, OneToOneRel):
                continue
            if not related.name.startswith('profile_'):
                continue

            profiles.append(getattr(self, related.name))

        return profiles


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
        verbose_name=_('amount'),
        help_text=_('The amount to be paid in the chosen interval'),
    )
    interval = models.IntegerField(
        choices=FeeIntervals.choices,
        verbose_name=_('interval'),
        help_text=_('How often does the member pay their fees?'),
    )
