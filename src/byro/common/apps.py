from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_save


class CommonConfig(AppConfig):
    name = "byro.common"


def user_save_receiver(sender, instance, created, **kwargs):
    if created:
        from byro.common.models import LogEntry

        LogEntry.objects.create(
            content_object=instance,
            action_type="byro.common.user.created",
            data={
                "source": "User creation checkpoint",
                "flags": {
                    "active": instance.is_active,
                    "superuser": instance.is_superuser,
                    "staff": instance.is_staff,
                },
            },
        )


post_save.connect(user_save_receiver, sender=settings.AUTH_USER_MODEL)
