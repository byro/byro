from hashlib import sha512

import magic
from django.apps import apps
from django.db import models, transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from byro.common.models import LogTargetMixin
from byro.common.models.choices import Choices


class DocumentDirection(Choices):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    OTHER = "other"


class Document(models.Model, LogTargetMixin):
    LOG_TARGET_BASE = "byro.documents.document"

    class Meta:
        ordering = ("-date", "title", "-id")

    document = models.FileField(upload_to="documents/%Y/%m/", max_length=1000)
    date = models.DateField(null=True, default=now)
    title = models.CharField(max_length=300, null=True)
    category = models.CharField(max_length=300, null=True)
    direction = models.CharField(
        choices=DocumentDirection.choices,
        max_length=DocumentDirection.max_length,
        default=DocumentDirection.OUTGOING,
    )
    member = models.ForeignKey(
        to="members.Member",
        related_name="documents",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    content_hash = models.CharField(max_length=300, null=True)

    template = _(
        """
Hi, {name},

Please find attached a document we wanted to send you/that you requested.

Thank you,
{association}
"""
    ).strip()

    def _get_log_properties(self):
        return {
            f.name: getattr(self, f.name)
            for f in self._meta.get_fields()
            if f.name not in ("id", "mails") and hasattr(self, f.name)
        }

    @cached_property
    def content_hash_ok(self):
        h = sha512()
        with self.document.open(mode="rb") as f:
            for chunk in f.chunks():
                h.update(chunk)
        return self.content_hash == "sha512:{}".format(h.hexdigest())

    @cached_property
    def mime_type_guessed(self):
        with self.document.open(mode="rb") as f:
            chunk = next(f.chunks())
            return magic.from_buffer(chunk, mime=True)

    @transaction.atomic
    def save(self, *args, **kwargs):

        retval = super().save(*args, **kwargs)

        # Only store the hash the first *time* that a file is added
        # Unfortunately we cannot do that on the first *save*, because
        # the API allows adding file content after the fact
        if self.document and not self.content_hash:
            h = sha512()
            with self.document.open(mode="rb") as f:
                for chunk in f.chunks():
                    h.update(chunk)
            self.content_hash = "sha512:{}".format(h.hexdigest())
            super().save(update_fields=["content_hash"])
            self.log(
                "internal: automatic checkpoint",
                ".stored",
                **self._get_log_properties()
            )

        return retval

    def send(self, immediately=False, text=None, subject=None, email=None):
        from byro.common.models import Configuration
        from byro.mails.models import EMail

        us = Configuration.get_solo().name
        mail = EMail.objects.create(
            to=email or self.member.email,
            text=text
            or self.template.format(
                name=self.member.name if self.member else email, association=us
            ),
            subject=_("[{association}] Your document").format(association=us),
        )
        mail.attachments.add(self)
        mail.save()
        if immediately:
            mail.send()
        return mail

    def get_display(self):
        return "{} Document: {}".format(
            self.get_direction_display().capitalize(), self.category, self.title
        )

    def get_absolute_url(self):
        return reverse("office:documents.detail", kwargs={"pk": self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-file-o"></i> ')


@receiver(pre_delete, sender=Document, dispatch_uid="documents_models__log_deletion")
def log_deletion(sender, instance, using, **kwargs):
    instance.log(
        "internal: automatic checkpoint", ".deleted", **instance._get_log_properties()
    )


def get_document_category_names():
    categories = {}

    for app in apps.get_app_configs():
        if hasattr(app, "ByroPluginMeta"):
            categories.update(getattr(app.ByroPluginMeta, "document_categories", {}))

    return categories
