from django.db import models
from django.utils.translation import ugettext_lazy as _

from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices


class DocumentDirection(Choices):
    INCOMING = 'incoming'
    OUTGOING = 'outgoing'

    valid_choices = [INCOMING, OUTGOING]


class Document(Auditable, models.Model):
    document = models.FileField(upload_to='documents/')
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

    template = _('''
Hi, {name},

Please find attached a document we wanted to send you/that you requested.

Thank you,
{association}
''').strip()

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
