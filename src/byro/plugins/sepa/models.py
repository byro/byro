from contextlib import suppress
from enum import Enum

from annoying.fields import AutoOneToOneField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from localflavor.generic.models import BICField, IBANField
from schwifty import BIC, IBAN

from byro.common.models.auditable import Auditable


class SepaDirectDebitState(Enum):
    OK = _("OK")
    NO_IBAN = _("No IBAN")
    INVALID_IBAN = _("Invalid IBAN")
    NO_BIC = _("No BIC")
    INVALID_BIC = _("Invalid BIC")
    BOUNCED = _("Debit bounced")
    RESCINDED = _("Mandate rescinded")
    INACTIVE = _("Direct debit deactivated")
    NO_MANDATE_REFERENCE = _("No mandate reference")


class MemberSepa(Auditable, models.Model):

    member = AutoOneToOneField(
        to="members.Member", related_name="profile_sepa", on_delete=models.PROTECT
    )

    iban = IBANField(null=True, blank=True, verbose_name="IBAN")
    bic = BICField(null=True, blank=True, verbose_name="BIC")

    mandate_state = models.CharField(
        choices=[
            ("inactive", _("Inactive")),
            ("active", _("Active")),
            ("bounced", _("Bounced")),
            ("rescinded", _("Rescinded")),
        ],
        default="active",
        max_length=10,
        blank=False,
        null=False,
        verbose_name=_("Mandate state"),
    )

    institute = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("IBAN Institute")
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("IBAN Issue Date"),
        help_text=_(
            "The issue date of the direct debit mandate. (1970-01-01 means there is no issue date in the database )"
        ),
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

    form_title = _("SEPA information")

    @property
    def is_usable(self):
        return self.sepa_direct_debit_state == SepaDirectDebitState.OK

    @property
    def iban_parsed(self):
        with suppress(ValueError):
            if self.iban:
                return IBAN(self.iban)

        return None

    @property
    def bic_autocomplete(self):
        if self.bic:
            return self.bic

        iban_parsed = self.iban_parsed
        if not iban_parsed:
            return None

        with suppress(ValueError):
            return str(iban_parsed.bic)

        return None

    @property
    def bic_parsed(self):
        with suppress(ValueError):
            bic = self.bic_autocomplete
            if bic:
                return BIC(bic)

        return None

    @property
    def sepa_direct_debit_state(self):
        if not self.iban:
            return SepaDirectDebitState.NO_IBAN

        if not self.iban_parsed:
            return SepaDirectDebitState.INVALID_IBAN

        if self.mandate_state == "rescinded":
            return SepaDirectDebitState.RESCINDED

        if self.mandate_state == "bounced":
            return SepaDirectDebitState.BOUNCED

        if self.mandate_state == "inactive":
            return SepaDirectDebitState.INACTIVE

        if not self.bic_autocomplete:
            return SepaDirectDebitState.NO_BIC

        bic = self.bic_parsed
        if not bic:
            return SepaDirectDebitState.INVALID_BIC

        if bic.country_code == "DE" and not bic.exists:
            # PBNKDEFF and PBNKDEFFXXX should be the same
            b_ = BIC(str(bic) + "XXX")
            if not b_.exists:
                return SepaDirectDebitState.INVALID_BIC

        if not self.mandate_reference:
            return SepaDirectDebitState.NO_MANDATE_REFERENCE

        return SepaDirectDebitState.OK
