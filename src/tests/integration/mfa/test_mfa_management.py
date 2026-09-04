from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import Client
from django.urls import reverse

from byro.common.models import LogEntry
from byro.mfa import services
from byro.mfa.models import MFAConfiguration, RecoveryCode, TOTPDevice


def run(*args, **kwargs):
    out = StringIO()
    call_command(*args, stdout=out, **kwargs)
    return out.getvalue()


@pytest.mark.django_db
def test_mfa_status_with_mfa(mfa_user, totp_device, recovery_codes):
    mfa_user.email = "admin@example.org"
    mfa_user.save()
    output = run("mfa_status", mfa_user.username)
    assert f"User: {mfa_user.username} (admin@example.org)" in output
    assert "MFA enabled: yes" in output
    assert "TOTP device: configured" in output
    assert "Recovery codes remaining: 10" in output
    assert "MFA required by policy: no" in output
    # never any secrets
    assert totp_device.base32_key not in output
    assert totp_device.manual_key not in output
    assert totp_device.encrypted_key not in output
    for code in recovery_codes:
        assert code not in output


@pytest.mark.django_db
def test_mfa_status_without_mfa(user, configuration):
    output = run("mfa_status", user.username)
    assert "MFA enabled: no" in output
    assert "TOTP device: not configured" in output

    TOTPDevice.create_pending(user)
    output = run("mfa_status", user.username)
    assert "setup started, not confirmed yet" in output


@pytest.mark.django_db
def test_mfa_status_lookup_by_email(mfa_user):
    mfa_user.email = "Admin@Example.org"
    mfa_user.save()
    output = run("mfa_status", "admin@example.org")
    assert "MFA enabled: yes" in output


@pytest.mark.django_db
def test_mfa_status_unknown_or_ambiguous_user(mfa_user):
    with pytest.raises(CommandError):
        run("mfa_status", "does-not-exist")
    mfa_user.email = "shared@example.org"
    mfa_user.save()
    get_user_model().objects.create(username="other", email="shared@example.org")
    with pytest.raises(CommandError):
        run("mfa_status", "shared@example.org")


@pytest.mark.django_db
def test_mfa_reset_requires_matching_confirmation(mfa_user, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "someone-else")
    with pytest.raises(CommandError):
        run("mfa_reset", mfa_user.username)
    assert services.user_has_mfa(mfa_user)
    assert not LogEntry.objects.filter(action_type=services.LOG_RESET).exists()


@pytest.mark.django_db
def test_mfa_reset_with_confirmation(
    verified_client, mfa_user, totp_device, recovery_codes, monkeypatch
):
    assert verified_client.get(reverse("office:dashboard")).status_code == 200
    monkeypatch.setattr("builtins.input", lambda prompt="": mfa_user.username)

    output = run("mfa_reset", mfa_user.username)
    assert "WARNING" in output
    assert "1 session(s) invalidated" in output
    assert totp_device.base32_key not in output

    assert not TOTPDevice.objects.filter(user=mfa_user).exists()
    assert not RecoveryCode.objects.filter(user=mfa_user).exists()
    entry = LogEntry.objects.get(action_type=services.LOG_RESET)
    assert entry.user is None
    assert entry.content_object == mfa_user
    assert entry.data["source"] == "internal: manage.py mfa_reset"
    assert entry.data["sessions_invalidated"] == 1

    # the user's session is gone
    response = verified_client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("common:login"))


@pytest.mark.django_db
def test_mfa_reset_force_skips_prompt(mfa_user, monkeypatch):
    def fail(prompt=""):
        raise AssertionError("input() must not be called with --force")

    monkeypatch.setattr("builtins.input", fail)
    output = run("mfa_reset", mfa_user.username, "--force")
    assert "removed" in output
    assert not services.user_has_mfa(mfa_user)
    assert MFAConfiguration.get_solo().require_mfa is False


@pytest.mark.django_db
def test_mfa_reset_only_terminates_sessions_of_that_user(
    verified_client, mfa_user, configuration, login_user
):
    other = get_user_model().objects.create(username="other_admin")
    other.set_password("test_password")
    other.save()
    other_client = Client()
    login_user(other_client, other)
    assert other_client.get(reverse("office:dashboard")).status_code == 200

    run("mfa_reset", mfa_user.username, "--force")

    assert other_client.get(reverse("office:dashboard")).status_code == 200
    assert verified_client.get(reverse("office:dashboard")).status_code == 302


@pytest.mark.django_db
def test_mfa_reset_mentions_policy(mfa_user, mfa_policy):
    output = run("mfa_reset", mfa_user.username, "--force")
    assert "required by policy" in output
    assert MFAConfiguration.get_solo().require_mfa is True
