import subprocess
import sys
from contextlib import suppress

from django.apps import apps


def get_plugins():
    result = []
    for app in apps.get_app_configs():
        if hasattr(app, "ByroPluginMeta"):
            if getattr(app, "name", "").startswith("byro.") and not hasattr(
                app.ByroPluginMeta, "version"
            ):
                continue
            result.append(app)
    return result


def get_version():
    with suppress(Exception):
        retval = getattr(sys.modules[__name__], "_byro_git_version", None)
        if retval:
            return retval

        retval = (
            subprocess.check_output(
                ["git", "describe", "--always", "--dirty", "--abbrev=40"],
                stderr=subprocess.PIPE,
            )
            .decode()
            .strip()
        )
        sys.modules[__name__]._byro_git_version = retval
        return retval

    with suppress(Exception):
        from byro import __version__

        return __version__

    return ""


def get_installed_software():
    retval = ["byro {}".format(get_version())]
    for plugin in get_plugins():
        retval.append(
            "{} {}".format(
                plugin.name, getattr(plugin.ByroPluginMeta, "version", "")
            ).strip()
        )
    return retval
