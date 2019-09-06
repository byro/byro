from django.apps import AppConfig


class PublicConfig(AppConfig):
    name = "byro.public"

    def ready(self):
        from . import signals  # noqa
