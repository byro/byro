import importlib

import pytest

from byro.common.settings import config as config_module


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
