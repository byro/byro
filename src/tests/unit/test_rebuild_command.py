import os
import sys

import pytest
from django.core.management import call_command

from byro.common.management.commands import rebuild


@pytest.fixture
def recorded_calls(monkeypatch):
    """Replace call_command inside the rebuild module and record (name, cwd)."""
    calls = []

    def fake_call_command(name, *args, **kwargs):
        calls.append((name, os.getcwd(), kwargs))

    monkeypatch.setattr(rebuild, "call_command", fake_call_command)
    return calls


def make_plugin(tmp_path, monkeypatch, name, with_locale=True, package=True):
    """Create an importable fake plugin package under tmp_path."""
    root = tmp_path / name
    root.mkdir()
    if package:
        (root / "__init__.py").write_text("")
    if with_locale:
        messages = root / "locale" / "de" / "LC_MESSAGES"
        messages.mkdir(parents=True)
        (messages / "django.po").write_text('msgid ""\nmsgstr ""\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, name, raising=False)
    return root


def test_rebuild_runs_asset_commands_in_order(recorded_calls, settings):
    settings.PLUGINS = []

    call_command("rebuild", verbosity=0)

    assert [name for name, _, _ in recorded_calls] == [
        "compilemessages",
        "collectstatic",
        "compress",
    ]
    kwargs_by_name = {name: kwargs for name, _, kwargs in recorded_calls}
    assert kwargs_by_name["collectstatic"]["interactive"] is False
    assert all(kwargs["verbosity"] == 0 for _, _, kwargs in recorded_calls)


def test_rebuild_compiles_plugin_translations_in_plugin_dir(
    recorded_calls, settings, tmp_path, monkeypatch
):
    plugin_root = make_plugin(tmp_path, monkeypatch, "fake_plugin")
    settings.PLUGINS = ["fake_plugin"]
    cwd_before = os.getcwd()

    call_command("rebuild", verbosity=0)

    assert [(name, cwd) for name, cwd, _ in recorded_calls] == [
        ("compilemessages", cwd_before),
        ("compilemessages", str(plugin_root.resolve())),
        ("collectstatic", cwd_before),
        ("compress", cwd_before),
    ]
    assert os.getcwd() == cwd_before


def test_rebuild_skips_plugins_without_locale(
    recorded_calls, settings, tmp_path, monkeypatch
):
    make_plugin(tmp_path, monkeypatch, "fake_plugin_bare", with_locale=False)
    settings.PLUGINS = ["fake_plugin_bare"]

    call_command("rebuild", verbosity=0)

    assert [name for name, _, _ in recorded_calls].count("compilemessages") == 1


def test_plugin_locale_roots_ignores_namespace_packages(
    settings, tmp_path, monkeypatch
):
    make_plugin(tmp_path, monkeypatch, "fake_namespace_plugin", package=False)
    settings.PLUGINS = ["fake_namespace_plugin"]

    assert list(rebuild.plugin_locale_roots()) == []


def test_rebuild_restores_cwd_when_plugin_compilemessages_fails(
    settings, tmp_path, monkeypatch
):
    make_plugin(tmp_path, monkeypatch, "fake_plugin_failing")
    settings.PLUGINS = ["fake_plugin_failing"]
    cwd_before = os.getcwd()

    def failing_call_command(name, *args, **kwargs):
        if os.getcwd() != cwd_before:
            raise RuntimeError("msgfmt failed")

    monkeypatch.setattr(rebuild, "call_command", failing_call_command)

    with pytest.raises(RuntimeError):
        call_command("rebuild", verbosity=0)
    assert os.getcwd() == cwd_before
