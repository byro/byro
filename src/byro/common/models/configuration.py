from django.conf.global_settings import LANGUAGES
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from solo.models import SingletonModel

from byro.common.models.choices import Choices
from byro.common.models.log import LogTargetMixin


class ByroConfiguration(LogTargetMixin, SingletonModel):
    """ Use this class to build a configuration set that will automatically
    show up on the office settings interface. """

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

    language = models.CharField(
        choices=LANGUAGES,
        null=True,
        blank=True,
        max_length=5,
        verbose_name=_("Language"),
    )
    currency = models.CharField(
        null=True,
        blank=True,
        max_length=3,
        verbose_name=_("Currency"),
        help_text=_("E.g. EUR"),
    )
    # Registration form configuration, contains settings for the fields to include when adding a new member
    registration_form = JSONField(null=True, blank=True)
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
