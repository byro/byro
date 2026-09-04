import re

import pytest
from django.contrib.auth.hashers import check_password
from django.urls import reverse

from byro.common.models import LogEntry
from byro.mfa import services
from byro.mfa.models import RecoveryCode

CODE_RE = re.compile(r"\b[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}\b")


@pytest.mark.django_db
def test_recovery_codes_are_stored_hashed(mfa_user, recovery_codes):
    stored = list(RecoveryCode.objects.filter(user=mfa_user))
    assert len(stored) == 10
    for code in recovery_codes:
        normalized = RecoveryCode.normalize(code)
        for entry in stored:
            assert code not in entry.code_hash
            assert normalized not in entry.code_hash
        assert any(check_password(normalized, entry.code_hash) for entry in stored)


@pytest.mark.django_db
def test_recovery_code_login(
    client, mfa_user, recovery_codes, configuration, login_user
):
    login_user(client, mfa_user)
    content = client.get(reverse("mfa:challenge")).content.decode()
    assert reverse("mfa:challenge.recovery") in content

    response = client.post(
        reverse("mfa:challenge.recovery"),
        {"code": recovery_codes[0], "next": reverse("office:members.list")},
    )
    assert response.status_code == 302
    assert response.url == reverse("office:members.list")

    response = client.get(reverse("office:members.list"))
    assert response.status_code == 200
    assert response.context["request"].user.is_verified()
    assert "9 recovery codes are left" in response.content.decode()

    assert RecoveryCode.objects.remaining_for(mfa_user) == 9
    assert (
        RecoveryCode.objects.filter(user=mfa_user, used_at__isnull=False).count() == 1
    )
    entry = LogEntry.objects.get(action_type=services.LOG_RECOVERY_CODE_USED)
    assert entry.user == mfa_user
    assert entry.data["remaining"] == 9
    assert recovery_codes[0] not in str(entry.data)


@pytest.mark.django_db
def test_recovery_code_cannot_be_reused(
    client, mfa_user, recovery_codes, configuration, login_user
):
    login_user(client, mfa_user)
    client.post(reverse("mfa:challenge.recovery"), {"code": recovery_codes[0]})
    client.get(reverse("common:logout"))

    login_user(client, mfa_user)
    response = client.post(
        reverse("mfa:challenge.recovery"), {"code": recovery_codes[0]}
    )
    assert response.status_code == 200
    assert "invalid or has expired" in response.content.decode()
    assert client.get(reverse("office:dashboard")).status_code == 302
    assert RecoveryCode.objects.remaining_for(mfa_user) == 9


@pytest.mark.django_db
def test_invalid_recovery_code_is_rejected(
    client, mfa_user, recovery_codes, configuration, login_user, totp_device
):
    login_user(client, mfa_user)
    response = client.post(
        reverse("mfa:challenge.recovery"), {"code": "AAAA-AAAA-AAAA"}
    )
    assert response.status_code == 200
    assert "invalid or has expired" in response.content.decode()
    totp_device.refresh_from_db()
    assert totp_device.throttling_failure_count == 1

    # malformed input is a form error, does not count as attempt
    response = client.post(reverse("mfa:challenge.recovery"), {"code": "abc"})
    assert response.status_code == 200
    totp_device.refresh_from_db()
    assert totp_device.throttling_failure_count == 1

    assert client.get(reverse("office:dashboard")).status_code == 302
    assert RecoveryCode.objects.remaining_for(mfa_user) == 10


@pytest.mark.django_db
def test_recovery_code_input_is_normalized(
    client, mfa_user, recovery_codes, configuration, login_user
):
    login_user(client, mfa_user)
    sloppy = " " + recovery_codes[3].lower().replace("-", " ") + " "
    response = client.post(reverse("mfa:challenge.recovery"), {"code": sloppy})
    assert response.status_code == 302
    assert client.get(reverse("office:dashboard")).status_code == 200


@pytest.mark.django_db
def test_recovery_link_hidden_without_codes(
    client, user, totp_device, configuration, login_user
):
    login_user(client, user)
    content = client.get(reverse("mfa:challenge")).content.decode()
    assert reverse("mfa:challenge.recovery") not in content


@pytest.mark.django_db
def test_regenerate_recovery_codes(
    verified_client, mfa_user, totp_device, recovery_codes, fresh_code, wrong_code
):
    response = verified_client.get(reverse("mfa:recovery-codes"))
    assert response.status_code == 200

    # wrong code: nothing changes
    response = verified_client.post(
        reverse("mfa:recovery-codes"), {"token": wrong_code(totp_device)}
    )
    assert response.status_code == 200
    assert "invalid or has expired" in response.content.decode()
    assert RecoveryCode.objects.consume(mfa_user, recovery_codes[0])
    assert not LogEntry.objects.filter(
        action_type=services.LOG_RECOVERY_CODES_REGENERATED
    ).exists()

    response = verified_client.post(
        reverse("mfa:recovery-codes"), {"token": fresh_code(totp_device)}
    )
    assert response.status_code == 200
    new_codes = CODE_RE.findall(response.content.decode())
    assert len(new_codes) == 10
    assert not set(new_codes) & set(recovery_codes)

    # old codes are gone, new ones work
    assert RecoveryCode.objects.remaining_for(mfa_user) == 10
    assert not RecoveryCode.objects.consume(mfa_user, recovery_codes[1])
    assert RecoveryCode.objects.consume(mfa_user, new_codes[0])
    assert LogEntry.objects.filter(
        action_type=services.LOG_RECOVERY_CODES_REGENERATED, user=mfa_user
    ).exists()


@pytest.mark.django_db
def test_regenerate_redirects_without_mfa(logged_in_client, configuration):
    response = logged_in_client.get(reverse("mfa:recovery-codes"))
    assert response.status_code == 302
    assert response.url == reverse("mfa:settings")


@pytest.mark.django_db
def test_consume_is_single_use(mfa_user, recovery_codes):
    assert RecoveryCode.objects.consume(mfa_user, recovery_codes[0])
    assert not RecoveryCode.objects.consume(mfa_user, recovery_codes[0])
    assert RecoveryCode.objects.remaining_for(mfa_user) == 9
