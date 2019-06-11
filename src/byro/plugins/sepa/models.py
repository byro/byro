from annoying.fields import AutoOneToOneField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from localflavor.generic.models import BICField, IBANField

from byro.common.models.auditable import Auditable


class MemberSepa(Auditable, models.Model):

    member = AutoOneToOneField(
        to='members.Member', related_name='profile_sepa', on_delete=models.PROTECT
    )

    iban = IBANField(null=True, blank=True, verbose_name="IBAN")
    bic = BICField(null=True, blank=True, verbose_name="BIC")

    mandate_state = models.CharField(
        choices=[
            ('inactive', _('Inactive')),
            ('active', _('Active')),
            ('bounced', _('Bounced')),
            ('rescinded', _('Rescinded')),
        ],
        default='active', max_length=10, blank=False, null=False,
        verbose_name=_("Mandate state"),
    )

    institute = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("IBAN Institute")
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("IBAN Issue Date"),
        help_text=_("The issue date of the direct debit mandate. (1970-01-01 means there is no issue date in the database )"),
    )

    fullname = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        verbose_name=_("IBAN full name"),
        help_text=_("Full name for IBAN account owner"),
    )

    address = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        verbose_name=_("IBAN address"),
        help_text=_("Address line (e.g. Street / House Number)"),
    )

    zip_code = models.CharField(
        null=True,
        blank=True,
        max_length=20,
        verbose_name=_("IBAN zip code"),
        help_text=_("ZIP Code"),
    )

    city = models.CharField(
        null=True, blank=True, max_length=255, verbose_name=_("IBAN City")
    )

    country = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        default="Deutschland",
        verbose_name=_("IBAN Country"),
    )

    mandate_reference = models.CharField(
        null=True, blank=True, max_length=255, verbose_name=_("IBAN Mandate Reference")
    )

    mandate_reason = models.CharField(
        null=True, blank=True, max_length=255, verbose_name=_("IBAN Mandate Reason")
    )

    form_title = _('SEPA information')

    @property
    def is_usable(self):
        return bool(self.iban and self.bic and self.mandate_reference)
