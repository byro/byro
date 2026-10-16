import os
import re
from hashlib import sha512

import magic
from django.apps import apps
from django.db import models, transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from byro.common.models import LogTargetMixin
from byro.common.models.choices import Choices

from .fields import FILENAME_MAX_LENGTH, DocumentFileField, document_storage_key

# Types the Office shows in the browser, detected from the content of the
# file. Everything else is only offered as a download.
INLINE_MIME_TYPES = frozenset(
    {"application/pdf", "image/gif", "image/jpeg", "image/png", "image/webp"}
)

# Characters that are not allowed in file names on common systems
UNSAFE_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*]')
# Characters that are dropped from the extension of a download name
UNSAFE_EXTENSION_CHARACTERS = re.compile(r"[^\w.-]")


def guess_mime_type(data):
    """The type of a file, detected from its first bytes."""
    return magic.from_buffer(data, mime=True)


def safe_download_name(value, max_length=150):
    """Make a title or name usable as the name of a downloaded file."""
    value = "".join(
        character if character.isprintable() else " " for character in str(value or "")
    )
    value = " ".join(UNSAFE_FILENAME_CHARACTERS.sub("_", value).split())
    return value.strip(" .")[:max_length].rstrip(" .")


class DocumentDirection(Choices):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    OTHER = "other"


class Document(models.Model, LogTargetMixin):
    LOG_TARGET_BASE = "byro.documents.document"

    class Meta:
        ordering = ("-date", "title", "-id")

    document = DocumentFileField(upload_to=document_storage_key, max_length=1000)
    # The name the file was handed to byro with, set by DocumentFieldFile.save().
    # For documents from before it was recorded, the last part of the old
    # storage key. Never part of the storage key itself.
    filename = models.CharField(
        max_length=FILENAME_MAX_LENGTH, blank=True, default="", editable=False
    )
    date = models.DateField(null=True, default=localdate)
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

    # Legacy compatibility attribute, kept for plugins that read it. send()
    # uses the configured document delivery mail template instead.
    template = _("""Hi, {name},

Please find attached a document we wanted to send you/that you requested.

Thank you,
{association}""").strip()

    def _get_log_properties(self):
        return {
            f.name: getattr(self, f.name)
            for f in self._meta.get_fields()
            if f.name not in ("id", "mails") and hasattr(self, f.name)
        }

    def open_file(self):
        """A new handle on the stored file, which the caller closes.

        Unlike ``self.document.open()``, this works repeatedly with every
        storage backend. Raises FileNotFoundError without a stored file.
        """
        if not self.document:
            raise FileNotFoundError("The document has no file.")
        return self.document.storage.open(self.document.name, "rb")

    def _calculate_hash(self):
        h = sha512()
        with self.open_file() as f:
            for chunk in f.chunks():
                h.update(chunk)
        return f"sha512:{h.hexdigest()}"

    @cached_property
    def content_hash_ok(self):
        return self.content_hash == self._calculate_hash()

    @cached_property
    def mime_type_guessed(self):
        with self.open_file() as f:
            return guess_mime_type(next(f.chunks()))

    @property
    def inline_mime_type(self):
        """The detected type if the browser may display the document, else None."""
        mime_type = self.mime_type_guessed
        return mime_type if mime_type in INLINE_MIME_TYPES else None

    @property
    def download_filename(self):
        """The name of the file in a download or a mail attachment: the title,
        else the category, else the original file name, with the extension
        of the original file."""
        extension = UNSAFE_EXTENSION_CHARACTERS.sub(
            "", os.path.splitext(self.filename)[1]
        )[:32]
        if len(extension) < 2:
            extension = ""
        category = get_document_category_names().get(self.category)
        for stem in (self.title, category):
            stem = safe_download_name(stem)
            if stem:
                if extension and stem.lower().endswith(extension.lower()):
                    return stem
                return stem + extension
        return safe_download_name(self.filename, FILENAME_MAX_LENGTH) or (
            f"document-{self.pk}" if self.pk else "document"
        )

    @transaction.atomic
    def save(self, *args, update_fields=None, **kwargs):
        saves_file = update_fields is None or "document" in update_fields
        if saves_file:
            # Store a newly assigned file before Django collects the values
            # of the row, because DocumentFieldFile.save() sets filename and
            # content_hash.
            self._meta.get_field("document").pre_save(self, add=self._state.adding)
            if update_fields is not None:
                update_fields = {*update_fields, "filename", "content_hash"}
        retval = super().save(*args, update_fields=update_fields, **kwargs)

        # A new file has no hash yet, see DocumentFieldFile.save(). The hash is
        # only calculated when the file itself is saved, a document can also
        # get its file after it was created.
        if saves_file and self.document and not self.content_hash:
            self.content_hash = self._calculate_hash()
            super().save(update_fields=["content_hash"])
            self.log(
                "internal: automatic checkpoint",
                ".stored",
                **self._get_log_properties(),
            )

        return retval

    def send(self, immediately=False, text=None, subject=None, email=None):
        """Place a mail with this document attached in the outbox.

        Subject and text come from the document delivery mail template. An
        explicit ``text`` or ``subject`` is used as given instead. A document
        without a member needs an explicit ``email``.
        """
        from byro.common.models import Configuration
        from byro.mails import default
        from byro.mails.models import MailTemplate

        if not email and self.member is None:
            raise ValueError(
                "A document without a member can only be sent to an explicit address."
            )
        config = Configuration.get_solo()
        template = config.document_delivery_template or MailTemplate(
            subject=default.DOCUMENT_DELIVERY_SUBJECT,
            text=default.DOCUMENT_DELIVERY_TEXT,
        )
        context = {
            "name": self.member.name if self.member else email,
            "association": config.name,
        }
        # An explicit address is a plain address. Without one, the document
        # goes to its member, who stays the recipient of the mail.
        recipient = {"email": email} if email else {"member": self.member}
        mail = template.to_mail(
            context=context,
            save=False,
            subject=subject or None,
            text=text or None,
            **recipient,
        )
        mail.save()
        mail.attachments.add(self)
        mail.save()
        if immediately:
            mail.send()
        return mail

    def get_display(self):
        return "{} [{}] Document: {}".format(
            self.get_direction_display().capitalize(), self.category, self.title
        )

    def get_absolute_url(self):
        return reverse("office:documents.detail", kwargs={"pk": self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-file-o"></i> ')

    @property
    def basename(self):
        """Deprecated, use ``filename``."""
        return self.filename


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
