from django.db import models

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
