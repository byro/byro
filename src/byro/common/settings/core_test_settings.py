"""Settings for byro's own test suite.

These are the regular test settings without the plugins that happen to be
installed in the Python environment, so that the result of the core tests
does not depend on the machine they run on. byro.settings only records the
module names of the ``byro.plugin`` entry points. Dropping them here, before
Django populates the app registry, means that no external plugin is imported
and none of its signal receivers is connected.

The plugins that ship with byro are listed in ``INSTALLED_APPS`` directly and
stay installed.

``byro.common.settings.test_settings`` keeps loading every installed plugin.
Plugin test suites use it, and the core tests can be run against the installed
plugins by selecting it (``--ds`` or ``DJANGO_SETTINGS_MODULE``).
"""

from byro.common.settings.test_settings import *  # noqa

INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in PLUGINS]  # noqa
PLUGINS = []
