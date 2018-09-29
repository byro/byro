from django.conf.global_settings import LANGUAGES
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from solo.models import SingletonModel


class ByroConfiguration(SingletonModel):
    """ Use this class to build a configuration set that will automatically
    show up on the office settings interface. """

    class Meta:
        abstract = True


class Configuration(ByroConfiguration):

    name = models.CharField(
        null=True, blank=True,
        max_length=100,
        verbose_name=_('Association name'),
    )
    address = models.TextField(
        null=True, blank=True,
        max_length=500,
        verbose_name=_('Association address'),
    )
    url = models.CharField(
        null=True, blank=True,
        max_length=200,
        verbose_name=_('Association URL'),
    )
    liability_interval = models.IntegerField(
        default=36,
        verbose_name=_('Statute of limitations'),
        help_text=_('For which interval can you make members pay their outstanding fees?'),
    )

    language = models.CharField(
        choices=LANGUAGES,
        null=True, blank=True,
        max_length=5,
        verbose_name=_('Language'),
    )
    currency = models.CharField(
        null=True, blank=True,
        max_length=3,
        verbose_name=_('Currency'),
        help_text=_('E.g. EUR')
    )
    # Registration form configuration, contains settings for the fields to include when adding a new member
    registration_form = JSONField(
        null=True, blank=True,
    )
    mail_from = models.EmailField(
        null=True, blank=True,
        max_length=100,
        verbose_name=_('E-mail address used as sender'),
    )
    backoffice_mail = models.EmailField(
        null=True, blank=True,
        max_length=100,
        verbose_name=_('E-mail address for notifications'),
    )
    welcome_member_template = models.ForeignKey(
        to='mails.MailTemplate',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    welcome_office_template = models.ForeignKey(
        to='mails.MailTemplate',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    leave_member_template = models.ForeignKey(
        to='mails.MailTemplate',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    leave_office_template = models.ForeignKey(
        to='mails.MailTemplate',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    record_disclosure_template = models.ForeignKey(
        to='mails.MailTemplate',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    form_title = _('General settings')
