from django.apps import AppConfig


class MFAConfig(AppConfig):
    name = "byro.mfa"
    label = "mfa"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        from . import signals  # noqa
        from .services import reset_session_verification

        # Every fresh login (password or OIDC) starts without MFA verification,
        # even if the browser session already existed.
        user_logged_in.connect(
            reset_session_verification, dispatch_uid="byro.mfa.reset_session"
        )
