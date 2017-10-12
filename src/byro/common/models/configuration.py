from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from solo.models import SingletonModel


class Configuration(SingletonModel):

    name = models.CharField(
        null=True, blank=True,
        max_length=100,
        verbose_name=_('name'),
    )
    address = models.CharField(
        null=True, blank=True,
        max_length=500,
        verbose_name=_('address'),
    )
    url = models.CharField(
        null=True, blank=True,
        max_length=200,
        verbose_name=_('url'),
    )

    language = models.CharField(
        null=True, blank=True,
        max_length=5,
        verbose_name=_('language'),
    )
    currency = models.CharField(
        null=True, blank=True,
        max_length=3,
        verbose_name=_('currency'),
    )

    registration_form = JSONField(
        null=True, blank=True,
        verbose_name=_('registration form configuration'),
    )
