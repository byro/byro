import contextlib
import importlib
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


def plugin_locale_roots():
    """Yield (module name, package directory) for every plugin with a locale/ dir.

    Django's compilemessages only walks the current working directory (and
    LOCALE_PATHS), so translations of plugins installed into site-packages are
    compiled from inside their package directory. Namespace packages have no
    __file__ and nothing to compile.
    """
    for module_name in getattr(settings, "PLUGINS", []):
        module = importlib.import_module(module_name)
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        root = Path(module_file).resolve().parent
        if (root / "locale").is_dir():
            yield module_name, root


class Command(BaseCommand):
    help = (
        "Rebuild translations and static assets: compilemessages (for byro and "
        "every installed plugin), collectstatic and (offline) compress. Run "
        "after installing or updating byro or a plugin, before restarting the "
        "web process."
    )

    def handle(self, *args, **options):
        verbosity = options.get("verbosity", 1)
        call_command("compilemessages", verbosity=verbosity)
        for module_name, root in plugin_locale_roots():
            if verbosity:
                self.stdout.write(
                    f"Compiling translations of plugin {module_name} ({root})"
                )
            with contextlib.chdir(root):
                call_command("compilemessages", verbosity=verbosity)
        call_command("collectstatic", interactive=False, verbosity=verbosity)
        call_command("compress", verbosity=verbosity)
