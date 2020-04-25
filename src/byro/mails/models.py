from copy import deepcopy

from django.db import models, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import override
from django.utils.translation import ugettext_lazy as _
from i18nfield.fields import I18nCharField, I18nTextField

from byro.common.models.auditable import Auditable
from byro.mails.send import SendMailException
from byro.members.models import Member


class MailTemplate(Auditable, models.Model):

    subject = I18nCharField(max_length=200, verbose_name=_("Subject"))
    text = I18nTextField(verbose_name=_("Text"))
    reply_to = models.EmailField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Reply-To"),
        help_text=_(
            "Change the Reply-To address if you do not want to use the default orga address"
        ),
    )
    bcc = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("BCC"),
        help_text=_(
            "Enter comma separated addresses. Will receive a blind copy of every mail sent from this template. This may be a LOT!"
        ),
    )

    def __str__(self):
        return "{self.subject}".format(self=self)

    def to_mail(
        self,
        email,
        locale=None,
        context=None,
        skip_queue=False,
        attachments=None,
        save=True,
    ):
        from byro.common.models import Configuration

        config = Configuration.get_solo()
        locale = locale or config.language
        with override(locale):
            context = context or dict()
            try:
                subject = str(self.subject).format(**context)
                text = str(self.text).format(**context)
            except KeyError as e:
                raise SendMailException(
                    "Experienced KeyError when rendering Text: {e}".format(e=e)
                )

            mail = EMail(
                to=email,
                reply_to=self.reply_to,
                bcc=self.bcc,
                subject=subject,
                text=text,
                template=self,
            )
            if save:
                mail.save()
                if attachments:
                    for a in attachments:
                        mail.attachments.add(a)
                if skip_queue:
                    mail.send()
        return mail

    def get_absolute_url(self):
        return reverse("office:mails.templates.view", kwargs={"pk": self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-envelope-o"></i> ')


class EMail(Auditable, models.Model):
    to = models.CharField(
        max_length=1000,
        verbose_name=_("To"),
        help_text=_("One email address or several addresses separated by commas."),
    )
    reply_to = models.CharField(
        max_length=1000, null=True, blank=True, verbose_name=_("Reply-To")
    )
    cc = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        verbose_name=_("CC"),
        help_text=_("One email address or several addresses separated by commas."),
    )
    bcc = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        verbose_name=_("BCC"),
        help_text=_("One email address or several addresses separated by commas."),
    )
    subject = models.CharField(max_length=200, verbose_name=_("Subject"))
    members = models.ManyToManyField(to="members.Member", related_name="emails")
    text = models.TextField(verbose_name=_("Text"))
    sent = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent at"))
    template = models.ForeignKey(
        to=MailTemplate, null=True, blank=True, on_delete=models.SET_NULL
    )
    attachments = models.ManyToManyField(to="documents.Document", related_name="mails")
    balance = models.ForeignKey(
        to="members.MemberBalance",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reminder_mails",
    )

    @property
    def attachment_ids(self):
        if hasattr(self, "attachments"):
            return list(self.attachments.all().values_list("pk", flat=True))
        return []

    def process_special_to(self):
        # Handles "special:" adresses, except "special:all" which is handled inside send()
        if self.to.startswith("special:"):
            if self.to.startswith("special:member:"):
                member = Member.all_objects.get(pk=self.to.split(":", 2)[2])
                self.to = member.email
                self.members.add(member)
                self.save(update_fields=["to"])

    @transaction.atomic
    def send(self):
        if self.sent:
            raise Exception("This mail has been sent already. It cannot be sent again.")

        self.process_special_to()

        from byro.common.models import Configuration

        config = Configuration.get_solo()

        if self.to == "special:all" or not self.to.startswith("special:"):
            send_tos = []

            if self.to == "special:all":
                for member in (
                    Member.objects.filter(
                        Q(memberships__start__lte=now().date())
                        & (
                            Q(memberships__end__isnull=True)
                            | Q(memberships__end__gte=now().date())
                        )
                    )
                    .filter(email__isnull=False)
                    .exclude(email="")
                    .all()
                ):
                    send_tos.append(member)
                    self.members.add(member)

            else:
                to_addrs = self.to.split(",")
                for addr in to_addrs:
                    member = Member.all_objects.filter(
                        email__iexact=addr.lower()
                    ).first()
                    if member:
                        send_tos.append(member)
                        self.members.add(member)
                    else:
                        send_tos.append(addr)

            headers = {}
            if self.reply_to:
                headers["Reply-To"] = self.reply_to

            from byro.mails.send import mail_send_task

            for addr in send_tos:
                body = self.text
                if isinstance(addr, Member):
                    signature = _(
                        "You are receiving this email due to your membership in {name}."
                    ).format(name=config.name)
                    signature += "\n"
                    signature += _(
                        "You can see your member page at this URL: {url}"
                    ).format(url=addr.profile_memberpage.get_url())
                    body += "\n\n-- \n" + signature
                    addr = addr.email
                mail_send_task(
                    to=[addr],
                    subject=self.subject,
                    body=body,
                    sender=config.mail_from,
                    cc=(self.cc or "").split(","),
                    bcc=(self.bcc or "").split(","),
                    attachments=self.attachment_ids,
                    headers=headers,
                )

        self.sent = now()
        self.save(update_fields=["sent"])

    def copy_to_draft(self):
        new_mail = deepcopy(self)
        new_mail.pk = None
        new_mail.sent = None
        new_mail.save()
        return new_mail
