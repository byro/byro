from django.apps import AppConfig


class SepaPluginConfig(AppConfig):
    name = "byro.plugins.sepa"

    def ready(self):
        from . import signals  # noqa
