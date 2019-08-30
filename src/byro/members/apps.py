from django.apps import AppConfig


class MemberConfig(AppConfig):
    name = "byro.members"

    def ready(self):
        from . import signals  # noqa
