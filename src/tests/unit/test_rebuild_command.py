from django.core.management import call_command

from byro.common.management.commands import rebuild


def test_rebuild_runs_asset_commands_in_order(monkeypatch):
    calls = []

    def fake_call_command(name, *args, **kwargs):
        calls.append((name, kwargs))

    monkeypatch.setattr(rebuild, "call_command", fake_call_command)

    call_command("rebuild", verbosity=0)

    assert [name for name, _ in calls] == [
        "compilemessages",
        "collectstatic",
        "compress",
    ]
    collectstatic_kwargs = dict(calls)["collectstatic"]
    assert collectstatic_kwargs["interactive"] is False
    assert all(kwargs["verbosity"] == 0 for _, kwargs in calls)
