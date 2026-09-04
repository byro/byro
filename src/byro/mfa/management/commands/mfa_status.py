from django.utils import formats, timezone

from byro.mfa import services
from byro.mfa.management.base import MFAUserCommand


class Command(MFAUserCommand):
    help = "Show the multi-factor authentication status of a user (no secrets)."

    def handle(self, *args, **options):
        user = self.get_user(options["user"])
        status = services.get_status(user)

        def yes_no(value):
            return "yes" if value else "no"

        def fmt(dt):
            if not dt:
                return "never"
            return formats.date_format(timezone.localtime(dt), "DATETIME_FORMAT")

        self.stdout.write(
            f"User: {user.get_username()}" + (f" ({user.email})" if user.email else "")
        )
        self.stdout.write(f"Active: {yes_no(user.is_active)}")
        self.stdout.write(f"MFA enabled: {yes_no(status.enabled)}")
        if status.enabled:
            self.stdout.write(
                f"TOTP device: configured (since {fmt(status.device.created_at)}, "
                f"last used {fmt(status.device.last_used_at)})"
            )
            self.stdout.write(
                f"Recovery codes remaining: {status.recovery_codes_remaining}"
            )
        elif status.pending_device is not None:
            self.stdout.write("TOTP device: setup started, not confirmed yet")
        else:
            self.stdout.write("TOTP device: not configured")
        self.stdout.write(
            f"MFA required by policy: {yes_no(status.required_by_policy)}"
        )
