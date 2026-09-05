from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Rebuild translations and static assets: compilemessages, "
        "collectstatic and (offline) compress. Run after installing or "
        "updating byro or a plugin, before restarting the web process."
    )

    def handle(self, *args, **options):
        verbosity = options.get("verbosity", 1)
        call_command("compilemessages", verbosity=verbosity)
        call_command("collectstatic", interactive=False, verbosity=verbosity)
        call_command("compress", verbosity=verbosity)
