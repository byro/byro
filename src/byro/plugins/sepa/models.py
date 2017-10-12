from annoying.fields import AutoOneToOneField
from django.db import models
from localflavor.generic.models import IBANField, BICField

from byro.common.models.auditable import Auditable


class MemberSepa(Auditable, models.Model):

    member = AutoOneToOneField(
        to='members.Member',
        related_name='profile_sepa',
        on_delete=models.PROTECT,
    )

    iban = IBANField(null=True, blank=True, verbose_name="IBAN")
    bic = BICField(null=True, blank=True, verbose_name="BIC")

    institute = models.CharField(
        max_length=255,
        null=True, blank=True,
        verbose_name="IBAN Institute")

    issue_date = models.DateField(
        null=True, blank=True,
        verbose_name="IBAN Issue Date",
        help_text="The issue date of the direct debit mandate. (1970-01-01 means there is no issue date in the database )")

    fullname = models.CharField(
        null=True, blank=True,
        max_length=255, verbose_name="IBAN full name",
        help_text="Full name for IBAN account owner")

    address = models.CharField(
        null=True, blank=True,
        max_length=255, verbose_name="IBAN address",
        help_text="Address line (e.g. Street / House Number)")

    zip_code = models.CharField(
        null=True, blank=True,
        max_length=20, verbose_name="IBAN zip code",
        help_text="ZIP Code")

    city = models.CharField(
        null=True, blank=True,
        max_length=255, verbose_name="IBAN City",)

    country = models.CharField(
        null=True, blank=True,
        max_length=255, default="Deutschland",
        verbose_name="IBAN Country",)

    mandate_reference = models.CharField(
        null=True, blank=True,
        max_length=255,
        verbose_name="IBAN Mandate Reference",)

    mandate_reason = models.CharField(
        null=True, blank=True,
        max_length=255,
        verbose_name="IBAN Mandate Reason",)
