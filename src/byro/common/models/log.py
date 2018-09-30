from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models


class ContentObjectManager(models.Manager):
    "An object manager that can handle filter(content_object=...)"
    def filter(self, *args, **kwargs):
        if 'content_object' in kwargs:
            content_object = kwargs.pop('content_object')
            kwargs['content_type'] = ContentType.objects.get_for_model(type(content_object))
            kwargs['object_id'] = content_object.pk
        return super().filter(*args, **kwargs)


class LogEntry(models.Model):
    """A log entry for a change (or addition, or modification) in the database.

    :param content_object: The object that was modified (or added)
    :param datetime: Timestamp of the logged action
    :param user: The user that performed the action
    :param action_type: dot-namespaced type of the action, such as "byro.office.members.add"
    :param data: arbitrary additional data about the action.
      Well-known keys:
        * source: Actor/initiator of the change (a user or an automatic process). This must always be present. Will be generated from user attribute if set.
        * old: Value before the change
        * new: Value after the change
    """
    content_type = models.ForeignKey(ContentType, null=True, on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    datetime = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(get_user_model(), null=True, on_delete=models.SET_NULL)

    action_type = models.CharField(max_length=255)
    data = JSONField(null=True)

    objects = ContentObjectManager()

    # FIXME Add pre-save signal, and, possibly, database-level protection against modification

    class Meta:
        ordering = ('-datetime', '-id')

    def delete(self, using=None, keep_parents=False):
        raise TypeError("Logs cannot be deleted.")

    def save(self, *args, **kwargs):
        if getattr(self, 'pk', None):
            raise TypeError("Logs cannot be modified.")

        if not self.data:
            self.data = {}

        if self.user:
            self.data.setdefault('source', str(self.user))

        if not self.data.get('source'):
            raise ValueError("Need to provide at least user or data['source']")

        return super().save(*args, **kwargs)


class LogTargetMixin:
    LOG_TARGET_BASE = None

    def log(self, context, action, user=None, **kwargs):
        if hasattr(context, 'request'):
            context = context.request

        user = user or getattr(context, 'user', None)

        if isinstance(context, str) and not 'source' in kwargs:
            kwargs['source'] = context

        if self.LOG_TARGET_BASE and action.startswith('.'):
            action = self.LOG_TARGET_BASE + action

        LogEntry.objects.create(content_object=self, user=user, action_type=action, data=dict(kwargs))
