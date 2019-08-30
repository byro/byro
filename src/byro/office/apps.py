from django.apps import AppConfig


class OfficeConfig(AppConfig):
    name = "byro.office"

    def ready(self):
        from . import signals  # noqa
