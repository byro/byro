from functools import wraps

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

        if isinstance(context, str) and 'source' not in kwargs:
            kwargs['source'] = context

        if self.LOG_TARGET_BASE and action.startswith('.'):
            action = self.LOG_TARGET_BASE + action

        LogEntry.objects.create(content_object=self, user=user, action_type=action, data=dict(kwargs))

    def log_entries(self):
        return LogEntry.objects.filter(content_object=self)


def log_call(action, log_on='retval'):
    def outer_decorator(f):
        @wraps(f)
        def decorator(*args, **kwargs):
            if 'user_or_context' not in kwargs:
                raise TypeError("You need to provide a 'user_or_context' named parameter which indicates the responsible user (a User model object), request (a View instance or HttpRequest object), or generic context (a str).")
            user_or_context = kwargs.pop('user_or_context')
            user = kwargs.pop('user', None)

            retval = f(*args, **kwargs)

            log_kwargs = {k: repr(v) for k, v in kwargs.items() if v}
            log_args = list(args)
            log_args = log_args[1:]   # Warning: we assume that args[0] is 'self'. Only works correctly with calls to bound methods
            if log_args:
                log_kwargs['_args'] = [repr(v) for v in log_args]

            if log_on == 'retval':
                retval.log(user_or_context, action, user=user, **log_kwargs)
            else:
                args[0].log(user_or_context, action, user=user, **log_kwargs)

            return retval

        return decorator

    return outer_decorator
