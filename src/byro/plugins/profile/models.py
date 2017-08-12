from django.db import models

from byro.common.models.auditable import Auditable


class MemberProfile(Auditable, models.Model):

    member = models.OneToOneField(
        to='members.Member',
        related_name='profile_profile',
        on_delete=models.PROTECT,
    )
    member_identifier = models.CharField(
        max_length=50,
        null=True,
    )
    birth_date = models.DateField(
        null=True
    )
    address = models.CharField(
        max_length=500,
        null=True
    )
    nick = models.CharField(
        max_length=200,
        null=True
    )
    name = models.CharField(
        max_length=200,
        null=True
    )
