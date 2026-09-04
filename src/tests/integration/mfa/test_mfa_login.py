import pytest
from django.urls import reverse

from byro.common.models import LogEntry


@pytest.mark.django_db
def test_login_without_mfa_is_unchanged(client, user, configuration, login_user):
    log_count = LogEntry.objects.count()
    login_user(client, user)
    assert LogEntry.objects.count() == log_count + 1  # byro.common.login.success

    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 200
    response = client.get(reverse("office:members.list"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_with_mfa_requires_challenge(client, mfa_user, configuration, login_user):
    login_user(client, mfa_user)

    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url == reverse("mfa:challenge") + "?next=%2F"

    response = client.get(reverse("office:members.list"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))
    assert "next=%2Fmembers%2Flist" in response.url

    # state changing requests are blocked as well
    response = client.post(reverse("office:members.add"), {"member__name": "X"})
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))

    # the user is authenticated, but not verified
    response = client.get(reverse("mfa:challenge"))
    assert response.status_code == 200
    assert response.context["request"].user.is_authenticated
    assert not response.context["request"].user.is_verified()


@pytest.mark.django_db
def test_challenge_wrong_code_denies_access(
    client, mfa_user, totp_device, configuration, login_user, wrong_code
):
    login_user(client, mfa_user)
    log_count = LogEntry.objects.count()

    response = client.post(
        reverse("mfa:challenge"), {"token": wrong_code(totp_device), "next": "/"}
    )
    assert response.status_code == 200
    assert "invalid or has expired" in response.content.decode()

    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    # failed attempts do not create audit log entries (like failed passwords)
    assert LogEntry.objects.count() == log_count
    totp_device.refresh_from_db()
    assert totp_device.throttling_failure_count == 1


@pytest.mark.django_db
def test_challenge_malformed_code_is_rejected(
    client, mfa_user, configuration, login_user
):
    login_user(client, mfa_user)
    for token in ("", "12345", "abcdef", "1234567"):
        response = client.post(reverse("mfa:challenge"), {"token": token})
        assert response.status_code == 200
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_challenge_correct_code_grants_access_and_keeps_next(
    client, mfa_user, totp_device, configuration, login_user, fresh_code
):
    login_user(client, mfa_user)
    target = reverse("office:members.list")

    response = client.get(reverse("mfa:challenge") + "?next=" + target)
    assert response.status_code == 200
    assert f'name="next" value="{target}"' in response.content.decode()

    response = client.post(
        reverse("mfa:challenge"), {"token": fresh_code(totp_device), "next": target}
    )
    assert response.status_code == 302
    assert response.url == target

    response = client.get(target)
    assert response.status_code == 200
    assert response.context["request"].user.is_verified()
    totp_device.refresh_from_db()
    assert totp_device.last_used_at is not None
    assert totp_device.throttling_failure_count == 0


@pytest.mark.django_db
def test_challenge_rejects_open_redirect(
    client, mfa_user, totp_device, configuration, login_user, fresh_code
):
    login_user(client, mfa_user)
    for evil in ("https://evil.example.com/", "//evil.example.com/x", "ftp://x/y"):
        response = client.post(
            reverse("mfa:challenge"), {"token": fresh_code(totp_device), "next": evil}
        )
        assert response.status_code == 302
        assert response.url == "/"


@pytest.mark.django_db
def test_totp_code_cannot_be_replayed(
    client, mfa_user, totp_device, configuration, login_user, fresh_code
):
    login_user(client, mfa_user)
    code = fresh_code(totp_device)
    response = client.post(reverse("mfa:challenge"), {"token": code, "next": "/"})
    assert response.status_code == 302

    client.get(reverse("common:logout"))
    login_user(client, mfa_user)
    response = client.post(reverse("mfa:challenge"), {"token": code, "next": "/"})
    assert response.status_code == 200
    assert "invalid or has expired" in response.content.decode()
    assert client.get(reverse("office:dashboard")).status_code == 302


@pytest.mark.django_db
def test_challenge_is_throttled_after_failure(
    client, mfa_user, totp_device, configuration, login_user, fresh_code, wrong_code
):
    login_user(client, mfa_user)
    response = client.post(
        reverse("mfa:challenge"), {"token": wrong_code(totp_device), "next": "/"}
    )
    assert response.status_code == 200

    # even the correct code is rejected while the device is locked
    good = fresh_code(totp_device)
    totp_device.throttling_failure_count = 1
    totp_device.throttling_failure_timestamp = totp_device.throttling_failure_timestamp
    from django.utils.timezone import now

    totp_device.throttling_failure_timestamp = now()
    totp_device.save()
    response = client.post(reverse("mfa:challenge"), {"token": good, "next": "/"})
    assert response.status_code == 200
    assert "Too many failed attempts" in response.content.decode()
    assert client.get(reverse("office:dashboard")).status_code == 302

    # after the lockout, the code works again
    response = client.post(
        reverse("mfa:challenge"), {"token": fresh_code(totp_device), "next": "/"}
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_logout_clears_verification(
    client, mfa_user, totp_device, configuration, login_user, fresh_code
):
    login_user(client, mfa_user)
    client.post(reverse("mfa:challenge"), {"token": fresh_code(totp_device)})
    assert client.get(reverse("office:dashboard")).status_code == 200

    client.get(reverse("common:logout"))
    assert client.get(reverse("office:dashboard")).status_code == 302  # to login

    login_user(client, mfa_user)
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))


@pytest.mark.django_db
def test_challenge_redirects_when_not_applicable(
    client, user, configuration, login_user
):
    # no device, no policy: nothing to verify
    login_user(client, user)
    response = client.get(reverse("mfa:challenge") + "?next=/members/list")
    assert response.status_code == 302
    assert response.url == "/members/list"
    response = client.get(reverse("mfa:challenge.recovery"))
    assert response.status_code == 302
    assert response.url == "/"


@pytest.mark.django_db
def test_challenge_redirects_when_already_verified(verified_client):
    response = verified_client.get(reverse("mfa:challenge") + "?next=/members/list")
    assert response.status_code == 302
    assert response.url == "/members/list"


@pytest.mark.django_db
def test_challenge_requires_login(client, configuration):
    response = client.get(reverse("mfa:challenge"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("common:login"))


@pytest.mark.django_db
def test_unverified_user_cannot_reach_mfa_management(
    client, mfa_user, configuration, login_user
):
    login_user(client, mfa_user)
    for name in (
        "mfa:settings",
        "mfa:setup",
        "mfa:recovery-codes",
        "mfa:disable",
    ):
        response = client.get(reverse(name))
        assert response.status_code == 302, name
        assert response.url.startswith(reverse("mfa:challenge")), name
        response = client.post(reverse(name), {"token": "123456"})
        assert response.status_code == 302, name
        assert response.url.startswith(reverse("mfa:challenge")), name


@pytest.mark.django_db
def test_unverified_user_can_log_out(client, mfa_user, configuration, login_user):
    login_user(client, mfa_user)
    response = client.get(reverse("common:logout"))
    assert response.status_code == 302
    assert response.url == "/"
    response = client.get(reverse("office:dashboard"))
    assert response.url.startswith(reverse("common:login"))


@pytest.mark.django_db
def test_challenge_page_shows_reduced_navigation(
    client, mfa_user, configuration, login_user
):
    login_user(client, mfa_user)
    content = client.get(reverse("mfa:challenge")).content.decode()
    assert reverse("common:logout") in content
    for name in (
        "office:members.list",
        "office:settings.base",
        "office:settings.users.list",
        "office:mails.outbox.list",
        "office:settings.api-token",
        "mfa:settings",
    ):
        assert f'href="{reverse(name)}"' not in content, name
    # the user menu only offers to log out
    assert f'class="dropdown-item" href="{reverse("common:logout")}"' in content
