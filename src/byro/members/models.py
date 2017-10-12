from django.db import models

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
    address = models.CharField(
        max_length=300,
        null=True, blank=True,
    )
    email = models.EmailField(
        max_length=200,
        null=True, blank=True,
    )

    @property
    def profiles(self) -> list:
        pass
