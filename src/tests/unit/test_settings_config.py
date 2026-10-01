import configparser
import importlib
import os
import subprocess
import sys

import pytest

from byro.common.settings import config as config_module
from byro.common.settings.utils import resolve_oidc_staff_group

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


@pytest.fixture
def reload_config(monkeypatch):
    """Reload the config module so that ``CONFIG`` picks up the patched
    environment, and restore the pristine module state afterwards."""

    def _reload():
        importlib.reload(config_module)
        return config_module

    yield _reload
    monkeypatch.undo()
    importlib.reload(config_module)


def test_trust_proxy_defaults_to_false(monkeypatch, reload_config):
    monkeypatch.delenv("BYRO_TRUST_PROXY", raising=False)
    module = reload_config()
    config, _ = module.build_config()
    assert config.getboolean("site", "trust_proxy") is False


@pytest.mark.parametrize("value", ["true", "True", "1", "yes"])
def test_trust_proxy_from_environment(monkeypatch, reload_config, value):
    monkeypatch.setenv("BYRO_TRUST_PROXY", value)
    module = reload_config()
    config, _ = module.build_config()
    assert config.getboolean("site", "trust_proxy") is True


def test_trust_proxy_false_from_environment(monkeypatch, reload_config):
    monkeypatch.setenv("BYRO_TRUST_PROXY", "false")
    module = reload_config()
    config, _ = module.build_config()
    assert config.getboolean("site", "trust_proxy") is False


# -- OIDC group options ------------------------------------------------------

OIDC_GROUP_ENV = (
    "BYRO_OIDC_STAFF_GROUP",
    "BYRO_OIDC_SUPERUSER_GROUP",
    "BYRO_OIDC_SYNC_GROUPS",
    "BYRO_OIDC_ADMIN_GROUP",
)


def test_oidc_group_options_default_to_off(monkeypatch, reload_config):
    for name in OIDC_GROUP_ENV:
        monkeypatch.delenv(name, raising=False)
    config = configparser.RawConfigParser()
    config = reload_config().read_layer("default", config)

    assert config.get("oidc", "staff_group") == ""
    assert config.get("oidc", "superuser_group") == ""
    assert config.get("oidc", "admin_group") == ""
    assert config.getboolean("oidc", "sync_groups") is False


def test_oidc_group_options_from_environment(monkeypatch, reload_config):
    monkeypatch.setenv("BYRO_OIDC_STAFF_GROUP", "byro-staff")
    monkeypatch.setenv("BYRO_OIDC_SUPERUSER_GROUP", "byro-superusers")
    monkeypatch.setenv("BYRO_OIDC_SYNC_GROUPS", "true")
    monkeypatch.setenv("BYRO_OIDC_ADMIN_GROUP", "byro-admins")
    config, _ = reload_config().build_config()

    assert config.get("oidc", "staff_group") == "byro-staff"
    assert config.get("oidc", "superuser_group") == "byro-superusers"
    assert config.getboolean("oidc", "sync_groups") is True
    # the deprecated option is still read, it is resolved in the settings
    assert config.get("oidc", "admin_group") == "byro-admins"


@pytest.mark.parametrize(
    "staff_group,admin_group,expected",
    (
        ("", "", ("", False)),
        ("byro-staff", "", ("byro-staff", False)),
        # an existing configuration that only knows the old name keeps working
        ("", "byro-admins", ("byro-admins", False)),
        ("  byro-staff ", " byro-staff", ("byro-staff", False)),
        (" admins ", "admins", ("admins", False)),
        ("   ", "", ("", False)),
        ("", "   ", ("", False)),
        ("   ", "byro-admins", ("byro-admins", False)),
        ("byro-staff", "\t ", ("byro-staff", False)),
        # no silent precedence: nothing is effective, the conflict is reported
        ("byro-staff", "byro-admins", ("", True)),
        (None, None, ("", False)),
    ),
)
def test_resolve_oidc_staff_group(staff_group, admin_group, expected):
    assert resolve_oidc_staff_group(staff_group, admin_group) == expected


@pytest.mark.parametrize(
    "environment,expected",
    (
        # an installation that only knows the deprecated name keeps its group
        ({"BYRO_OIDC_ADMIN_GROUP": "byro-admins"}, "byro-admins|False|byro-admins"),
        ({"BYRO_OIDC_STAFF_GROUP": "byro-staff"}, "byro-staff|False|"),
        (
            {"BYRO_OIDC_ADMIN_GROUP": "same", "BYRO_OIDC_STAFF_GROUP": "same"},
            "same|False|same",
        ),
        (
            {"BYRO_OIDC_ADMIN_GROUP": "one", "BYRO_OIDC_STAFF_GROUP": "other"},
            "|True|one",
        ),
        # the same normalisation byroctl applies: surrounding whitespace does
        # not count, and nothing but whitespace is not set
        (
            {"BYRO_OIDC_ADMIN_GROUP": " admins ", "BYRO_OIDC_STAFF_GROUP": "admins"},
            "admins|False|admins",
        ),
        ({"BYRO_OIDC_ADMIN_GROUP": "   "}, "|False|"),
        (
            {"BYRO_OIDC_ADMIN_GROUP": "   ", "BYRO_OIDC_STAFF_GROUP": "byro-staff"},
            "byro-staff|False|",
        ),
        (
            {"BYRO_OIDC_ADMIN_GROUP": "admins", "BYRO_OIDC_STAFF_GROUP": "   "},
            "admins|False|admins",
        ),
        (
            {"BYRO_OIDC_ADMIN_GROUP": " admins ", "BYRO_OIDC_STAFF_GROUP": " other "},
            "|True|admins",
        ),
    ),
)
def test_settings_resolve_the_deprecated_admin_group(environment, expected):
    """The real settings module, loaded in a fresh interpreter."""
    env = {key: value for key, value in os.environ.items() if key not in OIDC_GROUP_ENV}
    env.update(environment, DJANGO_SETTINGS_MODULE="byro.settings")
    code = (
        "from django.conf import settings as s;"
        "print('RESULT', s.OIDC_STAFF_GROUP, s.OIDC_GROUP_CONFLICT,"
        " s.OIDC_ADMIN_GROUP, sep='|')"
    )
    output = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        cwd=SRC_DIR,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    result = [line for line in output.splitlines() if line.startswith("RESULT|")]
    assert result == ["RESULT|" + expected]
