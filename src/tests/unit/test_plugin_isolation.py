"""Which settings load plugins that are installed next to byro (issue #567).

Settings and the app registry are initialised once per interpreter, so every
case runs in a fresh one. The ``byro.plugin`` entry points are replaced by a
single fake plugin there: the tests neither need an installed plugin package
nor see the plugins of the environment they run in.
"""

import json
import os
import subprocess
import sys
import textwrap

import pytest

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
FAKE_PLUGIN = "byro_fake_plugin"
BUNDLED_PLUGINS = ["byro.plugins.profile", "byro.plugins.sepa"]

FAKE_PLUGIN_APPS = """
from django.apps import AppConfig


class FakeImporter:
    identifier = "byro_fake_plugin.fake"
    label = "Fake"

    def parse(self, *args, **kwargs):
        return []


def importers(sender, **kwargs):
    return FakeImporter()


class FakePluginApp(AppConfig):
    name = "byro_fake_plugin"

    class ByroPluginMeta:
        name = "Fake plugin"
        version = "1.0.0"

    def ready(self):
        from byro.bookkeeping.signals import bank_transaction_importers

        bank_transaction_importers.connect(importers, dispatch_uid=self.name)
"""

PROBE = """
import importlib.metadata
import json
import sys

real_entry_points = importlib.metadata.entry_points


def entry_points(**params):
    if params.get("group") != "byro.plugin":
        return real_entry_points(**params)
    return [
        importlib.metadata.EntryPoint(
            name="byro_fake_plugin",
            value="byro_fake_plugin:ByroPluginMeta",
            group="byro.plugin",
        )
    ]


importlib.metadata.entry_points = entry_points

import django
from django.apps import apps
from django.conf import settings

django.setup()

from byro.bookkeeping.bank_import.registry import get_bank_transaction_importers

print(
    "RESULT"
    + json.dumps(
        {
            "plugins": settings.PLUGINS,
            "in_installed_apps": "byro_fake_plugin" in settings.INSTALLED_APPS,
            "app_loaded": apps.is_installed("byro_fake_plugin"),
            "module_imported": "byro_fake_plugin" in sys.modules,
            "receiver_connected": "byro_fake_plugin.fake"
            in get_bank_transaction_importers(),
            "bundled_plugins": [
                name
                for name in ("byro.plugins.profile", "byro.plugins.sepa")
                if apps.is_installed(name)
            ],
        }
    )
)
"""

LOADED = {
    "plugins": [FAKE_PLUGIN],
    "in_installed_apps": True,
    "app_loaded": True,
    "module_imported": True,
    "receiver_connected": True,
    "bundled_plugins": BUNDLED_PLUGINS,
}
IGNORED = {
    "plugins": [],
    "in_installed_apps": False,
    "app_loaded": False,
    "module_imported": False,
    "receiver_connected": False,
    "bundled_plugins": BUNDLED_PLUGINS,
}


@pytest.fixture
def probe_settings(tmp_path):
    """Set up Django with the given settings module in a fresh interpreter,
    with the fake plugin as the only ``byro.plugin`` entry point, and report
    what became of it."""
    package = tmp_path / "plugin" / FAKE_PLUGIN
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "apps.py").write_text(textwrap.dedent(FAKE_PLUGIN_APPS))

    def probe(settings_module):
        env = dict(
            os.environ,
            DJANGO_SETTINGS_MODULE=settings_module,
            BYRO_DATA_DIR=str(tmp_path / "data"),
            PYTHONPATH=os.pathsep.join(
                filter(None, [str(package.parent), os.environ.get("PYTHONPATH")])
            ),
        )
        output = subprocess.run(
            [sys.executable, "-c", PROBE],
            env=env,
            cwd=SRC_DIR,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        (result,) = [line for line in output.splitlines() if line.startswith("RESULT")]
        return json.loads(result.removeprefix("RESULT"))

    return probe


def test_core_test_suite_ignores_external_plugins(pytestconfig, probe_settings):
    """The settings module configured for the core test suite, whatever a
    ``--ds`` option or the environment selected for the current run. The
    plugins that ship with byro stay installed."""
    settings_module = pytestconfig.getini("DJANGO_SETTINGS_MODULE")
    assert probe_settings(settings_module) == IGNORED


def test_regular_settings_discover_external_plugins(probe_settings):
    assert probe_settings("byro.settings") == LOADED


def test_test_settings_load_external_plugins(probe_settings):
    """The explicit choice for running tests with the installed plugins, and
    the settings module that plugin test suites use."""
    assert probe_settings("byro.common.settings.test_settings") == LOADED
