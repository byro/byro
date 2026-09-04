import time

import pytest
from django.urls import reverse
from django_otp.oath import TOTP

from byro.mfa.models import MFAConfiguration, RecoveryCode, TOTPDevice


@pytest.fixture(autouse=True)
def fast_password_hashers(settings):
    # Recovery codes are stored with Django's password hashers. PBKDF2 with a
    # million iterations per code would make this test module very slow.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def mfa_policy(configuration):
    config = MFAConfiguration.get_solo()
    config.require_mfa = True
    config.save()
    return config


@pytest.fixture
def totp_code():
    """Return a callable computing the current TOTP code of a device."""

    def compute(device, offset=0):
        totp = TOTP(device.bin_key, device.STEP, device.T0, device.DIGITS, device.drift)
        totp.time = time.time() + offset * device.STEP
        return f"{totp.token():0{device.DIGITS}d}"

    return compute


@pytest.fixture
def fresh_code(totp_code):
    """Return a callable that resets replay protection and throttling of a
    device and returns a currently valid code, so tests can verify more than
    once within the same 30 second window."""

    def compute(device):
        device.refresh_from_db()
        device.last_t = -1
        device.drift = 0
        device.throttling_failure_count = 0
        device.throttling_failure_timestamp = None
        device.save()
        return totp_code(device)

    return compute


@pytest.fixture
def wrong_code(totp_code):
    def compute(device):
        current = totp_code(device)
        return "000000" if current != "000000" else "000001"

    return compute


@pytest.fixture
def totp_device(user):
    device = TOTPDevice.create_pending(user)
    device.confirmed = True
    device.save()
    return device


@pytest.fixture
def recovery_codes(totp_device, user):
    return RecoveryCode.objects.regenerate_for(user)


@pytest.fixture
def mfa_user(user, totp_device, recovery_codes):
    """A user with a confirmed authenticator and ten recovery codes."""
    return user


@pytest.fixture
def verified_client(
    client, mfa_user, totp_device, configuration, login_user, fresh_code
):
    """A client that passed password and TOTP challenge."""
    login_user(client, mfa_user)
    response = client.post(
        reverse("mfa:challenge"), {"token": fresh_code(totp_device), "next": "/"}
    )
    assert response.status_code == 302
    return client


def challenge_url(next_url="/"):
    return reverse("mfa:challenge") + "?next=" + next_url


def setup_url():
    return reverse("mfa:setup")
