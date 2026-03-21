from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "byro.api"

    def ready(self):
        from . import signals  # noqa
