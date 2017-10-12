from django.db import models

from annoying.fields import AutoOneToOneField

from byro.common.models.auditable import Auditable


class MemberProfile(Auditable, models.Model):

    member = AutoOneToOneField(
        to='members.Member',
        related_name='profile_profile',
        on_delete=models.PROTECT,
    )
    nick = models.CharField(
        max_length=200,
        null=True
    )
    birth_date = models.DateField(
        null=True
    )
    phone_number = models.CharField(
        max_length=32,
        blank=True, null=True
    )
