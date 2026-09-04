from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class MFAUserCommand(BaseCommand):
    """Base class for commands operating on a single user, identified by
    username or (unique) e-mail address."""

    def add_arguments(self, parser):
        parser.add_argument(
            "user", help="Username or (unique) e-mail address of the user"
        )

    def get_user(self, identifier):
        User = get_user_model()
        identifier = (identifier or "").strip()
        if not identifier:
            raise CommandError("Please specify a user.")
        user = User.objects.filter(username=identifier).first()
        if user is None and "@" in identifier:
            matches = list(User.objects.filter(email__iexact=identifier)[:2])
            if len(matches) > 1:
                raise CommandError(
                    f"More than one user has the e-mail address '{identifier}', "
                    "please use the username."
                )
            if matches:
                user = matches[0]
        if user is None:
            raise CommandError(f"No user found for '{identifier}'.")
        return user
