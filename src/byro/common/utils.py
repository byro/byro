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
    # FIXME: In a release this should return the version

    with suppress(Exception):
        retval = getattr(sys.modules[__name__], "_byro_git_version", None)
        if retval:
            return retval

        import subprocess

        retval = (
            subprocess.check_output(
                ["git", "describe", "--always", "--dirty", "--abbrev=40"]
            )
            .decode()
            .strip()
        )
        sys.modules[__name__]._byro_git_version = retval

        return retval

    return None


def get_installed_software():
    retval = ["byro {}".format(get_version())]
    for plugin in get_plugins():
        retval.append(
            "{} {}".format(
                plugin.name, getattr(plugin.ByroPluginMeta, "version", "")
            ).strip()
        )
    return retval
