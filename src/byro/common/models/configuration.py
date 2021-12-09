from django.conf.global_settings import LANGUAGES
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel

from byro.common.models.choices import Choices
from byro.common.models.log import LogTargetMixin


class ByroConfiguration(LogTargetMixin, SingletonModel):
    """Use this class to build a configuration set that will automatically show
    up on the office settings interface."""

    class Meta:
        abstract = True


class MemberViewLevel(Choices):
    NO = "no"
    NAME_ONLY = "name-only"
    NAME_AND_CONTACT = "name-contact"


class Configuration(ByroConfiguration):
    LOG_TARGET_BASE = "byro.settings"

    name = models.CharField(
        null=True, blank=True, max_length=100, verbose_name=_("Association name")
    )
    address = models.TextField(
        null=True, blank=True, max_length=500, verbose_name=_("Association address")
    )
    url = models.CharField(
        null=True, blank=True, max_length=200, verbose_name=_("Association URL")
    )
    liability_interval = models.IntegerField(
        default=36,
        verbose_name=_("Statute of limitations"),
        help_text=_(
            "For which interval can you make members pay their outstanding fees?"
        ),
    )
    accounting_start = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Start accounting Membership Fees from"),
        help_text=_(
            "This field is especially useful if the organization was later migrated to byro and the membership fees of members from the past are not to be billed. Leave the field empty if you do not have this requirement and you want to invoice all members from the beginning of their membership."
        ),
    )
    language = models.CharField(
        choices=LANGUAGES,
        null=True,
        blank=True,
        max_length=7,
        verbose_name=_("Language"),
    )
    currency = models.CharField(
        null=True,
        blank=True,
        max_length=3,
        verbose_name=_("Currency"),
        help_text=_("E.g. EUR"),
    )
    currency_symbol = models.CharField(
        default="€",
        max_length=8,
        verbose_name=_("Currency symbol"),
        help_text=_("E.g. €"),
    )
    currency_postfix = models.BooleanField(
        default=True,
        verbose_name=_("Show currency symbol after value"),
        help_text=_(
            "Controls whether the currency symbol comes before or after the monetary value"
        ),
    )
    display_cents = models.BooleanField(
        default=True,
        verbose_name=_("Display cents"),
        help_text=_(
            "When enabled, monetary values include two decimal fractional digits"
        ),
    )
    # Registration form configuration, contains settings for the fields to include when adding a new member
    registration_form = models.JSONField(null=True, blank=True)
    default_order_name = models.CharField(
        max_length=5,
        verbose_name=_("Default sort order"),
        help_text=_(
            "You can always override the automatic sort order if a member has an unusual name."
        ),
        choices=(
            ("first", _("First part of the name")),
            ("last", _("Last part of the name")),
        ),
        default="last",
    )
    default_direct_address_name = models.CharField(
        max_length=5,
        verbose_name=_("Default name when addressing members"),
        help_text=_(
            "This is used in emails, for example. You can always override the automatically chosen name if a member has an unusual name."
        ),
        choices=(
            ("first", _("First part of the name")),
            ("last", _("Last part of the name")),
        ),
        default="first",
    )
    public_base_url = models.URLField(  # Do we want this here or in the settings.py next to SITE_URL?
        max_length=512,
        null=True,
        blank=True,
        verbose_name=_("External base URL of byro installation"),
        help_text=_(
            "This field is used to generate the absolute URL for public pages. Leave it empty if it is the same as this page's base URL."
        ),
    )
    mail_from = models.EmailField(
        null=True,
        blank=True,
        max_length=100,
        verbose_name=_("E-mail address used as sender"),
    )
    backoffice_mail = models.EmailField(
        null=True,
        blank=True,
        max_length=100,
        verbose_name=_("E-mail address for notifications"),
    )
    welcome_member_template = models.ForeignKey(
        to="mails.MailTemplate",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    welcome_office_template = models.ForeignKey(
        to="mails.MailTemplate",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    leave_member_template = models.ForeignKey(
        to="mails.MailTemplate",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    leave_office_template = models.ForeignKey(
        to="mails.MailTemplate",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    record_disclosure_template = models.ForeignKey(
        to="mails.MailTemplate",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    form_title = _("General settings")

    def __str__(self):
        return "Settings"

    def get_absolute_url(self):
        return reverse("office:settings.base")
