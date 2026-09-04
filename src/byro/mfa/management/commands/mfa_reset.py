from django.conf import settings
from django.core.management.base import CommandError

from byro.mfa import services
from byro.mfa.management.base import MFAUserCommand

SOURCE = "internal: manage.py mfa_reset"


class Command(MFAUserCommand):
    help = (
        "Break-glass recovery: remove all MFA credentials (authenticator and "
        "recovery codes) of a user and terminate their sessions. Does NOT change "
        "the global MFA policy – if MFA is required, the user has to set it up "
        "again at the next login."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--force",
            action="store_true",
            help="Do not ask for interactive confirmation.",
        )

    def handle(self, *args, **options):
        user = self.get_user(options["user"])
        username = user.get_username()
        status = services.get_status(user)

        self.stdout.write(self.style.WARNING("WARNING:"))
        self.stdout.write("")
        self.stdout.write(
            "This will remove all MFA credentials and recovery codes for:"
        )
        self.stdout.write("")
        self.stdout.write(
            f"    {username}" + (f" ({user.email})" if user.email else "")
        )
        self.stdout.write("")
        if not status.enabled and status.pending_device is None:
            self.stdout.write("Note: this user has no MFA credentials at the moment.")
        self.stdout.write("Existing sessions will be invalidated.")
        self.stdout.write("")

        if not options["force"]:
            answer = input("Type the username to confirm: ")
            if answer.strip() != username:
                raise CommandError("Confirmation failed, nothing was changed.")

        sessions = services.reset_mfa(user, source=SOURCE)

        self.stdout.write(
            self.style.SUCCESS(
                f"MFA credentials of '{username}' removed, "
                f"{sessions} session(s) invalidated."
            )
        )
        if not settings.SESSION_ENGINE.endswith(".db"):
            self.stdout.write(
                self.style.WARNING(
                    "Note: sessions are not stored in the database (SESSION_ENGINE="
                    f"{settings.SESSION_ENGINE}), existing sessions could not be "
                    "terminated automatically."
                )
            )
        if status.required_by_policy:
            self.stdout.write(
                "MFA is required by policy: the user has to set up MFA again at "
                "their next login. The policy itself is unchanged."
            )
        else:
            self.stdout.write("The user can log in with their password only again.")
