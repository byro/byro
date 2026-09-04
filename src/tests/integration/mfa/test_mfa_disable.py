import pytest
from django.urls import reverse

from byro.common.models import LogEntry
from byro.mfa import services
from byro.mfa.models import RecoveryCode, TOTPDevice


@pytest.mark.django_db
def test_disable_requires_totp(
    verified_client, mfa_user, totp_device, fresh_code, wrong_code, login_user
):
    response = verified_client.get(reverse("mfa:disable"))
    assert response.status_code == 200

    response = verified_client.post(
        reverse("mfa:disable"), {"token": wrong_code(totp_device)}
    )
    assert response.status_code == 200
    assert "invalid or has expired" in response.content.decode()
    assert services.user_has_mfa(mfa_user)

    response = verified_client.post(
        reverse("mfa:disable"), {"token": fresh_code(totp_device)}
    )
    assert response.status_code == 302
    assert response.url == reverse("mfa:settings")

    assert not TOTPDevice.objects.filter(user=mfa_user).exists()
    assert not RecoveryCode.objects.filter(user=mfa_user).exists()
    entry = LogEntry.objects.get(action_type=services.LOG_DISABLED)
    assert entry.user == mfa_user
    assert entry.content_object == mfa_user

    response = verified_client.get(reverse("mfa:settings"))
    assert response.status_code == 200
    assert "Not configured" in response.content.decode()
    assert not response.context["request"].user.is_verified()

    # the account works with the password only again
    verified_client.get(reverse("common:logout"))
    login_user(verified_client, mfa_user)
    assert verified_client.get(reverse("office:dashboard")).status_code == 200


@pytest.mark.django_db
def test_disable_redirects_without_mfa(logged_in_client, configuration):
    response = logged_in_client.get(reverse("mfa:disable"))
    assert response.status_code == 302
    assert response.url == reverse("mfa:settings")


@pytest.mark.django_db
def test_disable_blocked_by_policy(
    verified_client, mfa_user, totp_device, mfa_policy, fresh_code
):
    content = verified_client.get(reverse("mfa:settings")).content.decode()
    assert reverse("mfa:disable") not in content
    assert "cannot be disabled" in content

    response = verified_client.get(reverse("mfa:disable"))
    assert response.status_code == 302
    assert response.url == reverse("mfa:settings")

    response = verified_client.post(
        reverse("mfa:disable"), {"token": fresh_code(totp_device)}
    )
    assert response.status_code == 302
    assert services.user_has_mfa(mfa_user)
    assert not LogEntry.objects.filter(action_type=services.LOG_DISABLED).exists()
