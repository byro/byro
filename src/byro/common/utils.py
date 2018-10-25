from contextlib import suppress

from django.apps import apps


def get_plugins():
    result = []
    for app in apps.get_app_configs():
        if hasattr(app, 'ByroPluginMeta'):
            if getattr(app, 'name', '').startswith("byro.") and not hasattr(app.ByroPluginMeta, 'version'):
                continue
            result.append(app)
    return result


def get_version():
    # FIXME: In a release this should return the version

    with suppress(Exception):
        import subprocess
        return subprocess.check_output(['git', 'describe', '--always', '--dirty', '--abbrev=40']).decode().strip()

    return None


def get_installed_software():
    retval = ["byro {}".format(get_version())]
    for plugin in get_plugins():
        retval.append("{} {}".format(plugin.name, getattr(plugin.ByroPluginMeta, 'version', '')).strip())
    return retval
