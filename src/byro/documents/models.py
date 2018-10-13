from hashlib import sha512

from django.db import models, transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from byro.common.models import LogTargetMixin, log_call
from byro.common.models.choices import Choices


class DocumentDirection(Choices):
    INCOMING = 'incoming'
    OUTGOING = 'outgoing'
    OTHER = 'other'


class Document(models.Model, LogTargetMixin):
    LOG_TARGET_BASE = 'byro.documents.document'

    class Meta:
        ordering = ('-date', 'title', '-id')

    document = models.FileField(upload_to='documents/%Y/%m/', max_length=1000)
    date = models.DateField(null=True, default=now)
    title = models.CharField(max_length=300, null=True)
    category = models.CharField(max_length=300, null=True)
    direction = models.CharField(
        choices=DocumentDirection.choices,
        max_length=DocumentDirection.max_length,
        default=DocumentDirection.OUTGOING,
    )
    member = models.ForeignKey(
        to='members.Member',
        related_name='documents',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    content_hash = models.CharField(max_length=300, null=True)

    template = _('''
Hi, {name},

Please find attached a document we wanted to send you/that you requested.

Thank you,
{association}
''').strip()

    @transaction.atomic
    def save(self, *args, **kwargs):

        retval = super().save(*args, **kwargs)

        # Only store the hash the first *time* that a file is added
        # Unfortunately we cannot do that on the first *save*, because
        # the API allows adding file content after the fact
        if self.document and not self.content_hash:
            h = sha512()
            with self.document.open(mode='rb') as f:
                for chunk in f.chunks():
                    h.update(chunk)
            self.content_hash = 'sha512:{}'.format(h.hexdigest())
            super().save(*args, **kwargs)
            self.log('internal: automatic checkpoint', '.stored', **{f.name: getattr(self, f.name) for f in self._meta.get_fields()})

        return retval

    def send(self, immediately=False, text=None, subject=None, email=None):
        from byro.common.models import Configuration
        from byro.mails.models import EMail
        us = Configuration.get_solo().name
        mail = EMail.objects.create(
            to=email or self.member.email,
            text=text or self.template.format(name=self.member.name if self.member else email, association=us),
            subject=_('[{association}] Your document').format(association=us)
        )
        mail.attachments.add(self)
        mail.save()
        if immediately:
            mail.send()
        return mail

    def get_display(self):
        return '{} Document: {}'.format(self.get_direction_display().capitalize(), self.category, self.title)


@receiver(pre_delete, sender=Document, dispatch_uid='documents_models__log_deletion')
def log_deletion(sender, instance, using, **kwargs):
    instance.log('internal: automatic checkpoint', '.deleted', **{f.name: getattr(instance, f.name) for f in instance._meta.get_fields()})
