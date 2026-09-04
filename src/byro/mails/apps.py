from django.apps import AppConfig


class MailsConfig(AppConfig):
    name = "byro.mails"

    def ready(self):
        from . import signals  # noqa
