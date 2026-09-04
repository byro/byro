import re
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import now

from byro.common.models import LogEntry
from byro.common.signals import periodic_task
from byro.mfa import services
from byro.mfa.models import RecoveryCode, TOTPDevice

CODE_RE = re.compile(r"\b[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}\b")


@pytest.mark.django_db
def test_settings_page_without_mfa(logged_in_client, configuration):
    response = logged_in_client.get(reverse("mfa:settings"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Not configured" in content
    assert reverse("mfa:setup") in content
    assert reverse("mfa:disable") not in content


@pytest.mark.django_db
def test_user_menu_links_to_personal_settings(logged_in_client, configuration):
    content = logged_in_client.get(reverse("office:dashboard")).content.decode()
    for name in ("mfa:settings", "office:settings.api-token", "common:logout"):
        assert f'class="dropdown-item" href="{reverse(name)}"' in content, name
    # personal settings are no longer part of the sidebar
    assert (
        f'class="nav-link nav-link-second-level " href="{reverse("office:settings.api-token")}"'
        not in content
    )
    assert content.count(reverse("office:settings.api-token")) == 1


@pytest.mark.django_db
def test_mfa_urls_live_under_settings_and_login():
    assert reverse("mfa:settings") == "/settings/mfa/"
    assert reverse("mfa:setup") == "/settings/mfa/setup/"
    assert reverse("mfa:recovery-codes") == "/settings/mfa/recovery-codes/"
    assert reverse("mfa:disable") == "/settings/mfa/disable/"
    assert reverse("mfa:challenge") == "/login/mfa/"
    assert reverse("mfa:challenge.recovery") == "/login/mfa/recovery/"


@pytest.mark.django_db
def test_setup_page_creates_pending_device_only(logged_in_client, user, configuration):
    response = logged_in_client.get(reverse("mfa:setup"))
    assert response.status_code == 200
    content = response.content.decode()

    device = TOTPDevice.objects.get(user=user)
    assert not device.confirmed
    assert not services.user_has_mfa(user)
    assert "data:image/png;base64," in content
    assert device.manual_key in content
    assert device.base32_key not in device.encrypted_key
    # secret is only ever shown as QR code / manual key, never the raw URL
    assert "otpauth://" not in content

    # opening the page again keeps the same pending secret
    response = logged_in_client.get(reverse("mfa:setup"))
    assert TOTPDevice.objects.filter(user=user).count() == 1
    assert device.manual_key in response.content.decode()

    # a pending device does not require MFA anywhere
    assert logged_in_client.get(reverse("office:dashboard")).status_code == 200


@pytest.mark.django_db
def test_setup_replaces_stale_pending_device(logged_in_client, user, configuration):
    logged_in_client.get(reverse("mfa:setup"))
    stale = TOTPDevice.objects.get(user=user)
    TOTPDevice.objects.filter(pk=stale.pk).update(created_at=now() - timedelta(hours=2))

    logged_in_client.get(reverse("mfa:setup"))
    devices = TOTPDevice.objects.filter(user=user)
    assert devices.count() == 1
    assert devices.get().pk != stale.pk


@pytest.mark.django_db
def test_setup_wrong_code_does_not_enable(
    logged_in_client, user, configuration, wrong_code
):
    logged_in_client.get(reverse("mfa:setup"))
    device = TOTPDevice.objects.get(user=user)

    response = logged_in_client.post(
        reverse("mfa:setup"), {"token": wrong_code(device)}
    )
    assert response.status_code == 200
    assert "invalid or has expired" in response.content.decode()
    device.refresh_from_db()
    assert not device.confirmed
    assert not services.user_has_mfa(user)
    assert RecoveryCode.objects.filter(user=user).count() == 0
    assert not LogEntry.objects.filter(action_type=services.LOG_ENABLED).exists()


@pytest.mark.django_db
def test_setup_correct_code_enables_mfa(
    logged_in_client, user, configuration, totp_code
):
    logged_in_client.get(reverse("mfa:setup"))
    device = TOTPDevice.objects.get(user=user)

    response = logged_in_client.post(
        reverse("mfa:setup"),
        {"token": totp_code(device), "next": reverse("office:members.list")},
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "now enabled" in content
    codes = CODE_RE.findall(content)
    assert len(codes) == 10
    assert len(set(codes)) == 10
    assert f'href="{reverse("office:members.list")}"' in content

    device.refresh_from_db()
    assert device.confirmed
    assert services.user_has_mfa(user)
    assert RecoveryCode.objects.remaining_for(user) == 10
    entry = LogEntry.objects.get(action_type=services.LOG_ENABLED)
    assert entry.user == user
    assert entry.content_object == user
    assert device.base32_key not in str(entry.data)

    # the session that completed the enrollment is verified
    response = logged_in_client.get(reverse("office:dashboard"))
    assert response.status_code == 200
    assert response.context["request"].user.is_verified()

    # status page: enabled, secret is not shown anymore
    content = logged_in_client.get(reverse("mfa:settings")).content.decode()
    assert "Enabled" in content
    assert "10 remaining" in content
    assert device.manual_key not in content
    assert device.base32_key not in content
    assert reverse("mfa:disable") in content


@pytest.mark.django_db
def test_setup_redirects_when_already_enabled(verified_client):
    response = verified_client.get(reverse("mfa:setup"))
    assert response.status_code == 302
    assert response.url == reverse("mfa:settings")


@pytest.mark.django_db
def test_setup_post_without_pending_device(logged_in_client, configuration):
    response = logged_in_client.post(reverse("mfa:setup"), {"token": "123456"})
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))


@pytest.mark.django_db
def test_abandoned_setup_does_not_require_mfa(client, user, configuration, login_user):
    login_user(client, user)
    client.get(reverse("mfa:setup"))
    client.get(reverse("common:logout"))

    login_user(client, user)
    assert client.get(reverse("office:dashboard")).status_code == 200


@pytest.mark.django_db
def test_next_login_requires_totp_after_enrollment(
    client, user, configuration, login_user, totp_code
):
    login_user(client, user)
    client.get(reverse("mfa:setup"))
    device = TOTPDevice.objects.get(user=user)
    client.post(reverse("mfa:setup"), {"token": totp_code(device)})
    client.get(reverse("common:logout"))

    login_user(client, user)
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))


@pytest.mark.django_db
def test_periodic_cleanup_removes_stale_pending_devices(user, configuration):
    stale = TOTPDevice.create_pending(user)
    TOTPDevice.objects.filter(pk=stale.pk).update(created_at=now() - timedelta(days=1))
    recent = TOTPDevice.create_pending(user)
    confirmed = TOTPDevice.create_pending(user)
    confirmed.confirmed = True
    confirmed.save()
    TOTPDevice.objects.filter(pk=confirmed.pk).update(
        created_at=now() - timedelta(days=30)
    )

    periodic_task.send(sender="test")

    remaining = set(TOTPDevice.objects.values_list("pk", flat=True))
    assert remaining == {recent.pk, confirmed.pk}
