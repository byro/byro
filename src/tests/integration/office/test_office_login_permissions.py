"""Backend access (login and session) for every combination of ``is_staff``
and ``is_superuser``."""

import pytest
from django.contrib.auth import SESSION_KEY
from django.shortcuts import reverse

from byro.common import views as common_views
from byro.common.models import LogEntry

NO_ACCESS = "byro.common.login.no_access"
NO_ACCESS_MESSAGE = "This account does not have access to the backend."

# (is_staff, is_superuser, may log in)
FLAG_COMBINATIONS = (
    pytest.param(False, False, False, id="no-flags"),
    pytest.param(True, False, True, id="staff"),
    pytest.param(False, True, True, id="superuser-without-staff"),
    pytest.param(True, True, True, id="staff-and-superuser"),
)


@pytest.fixture
def oidc_callback(monkeypatch):
    """Run the OIDC callback for a given local account without talking to an
    identity provider."""

    def callback(client, user):
        monkeypatch.setattr(common_views, "is_oidc_configured", lambda: True)
        monkeypatch.setattr(
            common_views,
            "exchange_code",
            lambda code, redirect_uri: {"id_token": "id", "access_token": "at"},
        )
        monkeypatch.setattr(
            common_views,
            "validate_id_token",
            lambda id_token, nonce: {"preferred_username": user.username},
        )
        monkeypatch.setattr(
            common_views, "get_or_create_user", lambda claims, access_token: user
        )
        session = client.session
        session["oidc_state"] = "state123"
        session["oidc_nonce"] = "nonce123"
        session.save()
        return client.get(reverse("common:oidc-callback") + "?state=state123&code=abc")

    return callback


def assert_logged_in(client, response, user, action_type):
    assert response.status_code == 302
    assert response.url == "/"
    assert client.session[SESSION_KEY] == str(user.pk)
    assert client.get(reverse("office:dashboard")).status_code == 200
    assert LogEntry.objects.filter(action_type=action_type).count() == 1
    assert not LogEntry.objects.filter(action_type=NO_ACCESS).exists()


def assert_rejected(client, response, user):
    assert response.status_code == 302
    assert response.url == reverse("common:login")
    assert SESSION_KEY not in client.session
    entry = LogEntry.objects.get(action_type=NO_ACCESS)
    assert entry.content_object == user
    assert entry.user == user
    assert not LogEntry.objects.filter(
        action_type__in=("byro.common.login.success", "byro.common.login.oidc")
    ).exists()

    response = client.get(reverse("office:dashboard"), follow=True)
    assert response.resolver_match.url_name == "login"
    assert NO_ACCESS_MESSAGE in response.content.decode()


@pytest.mark.parametrize("is_staff,is_superuser,allowed", FLAG_COMBINATIONS)
@pytest.mark.django_db
def test_password_login(
    client, create_user, configuration, is_staff, is_superuser, allowed
):
    user = create_user("someone", is_staff=is_staff, is_superuser=is_superuser)

    response = client.post(
        reverse("common:login"),
        {"username": user.username, "password": "test_password"},
    )

    if allowed:
        assert_logged_in(client, response, user, "byro.common.login.success")
    else:
        assert_rejected(client, response, user)


@pytest.mark.parametrize("is_staff,is_superuser,allowed", FLAG_COMBINATIONS)
@pytest.mark.django_db
def test_oidc_login(
    client, create_user, configuration, oidc_callback, is_staff, is_superuser, allowed
):
    user = create_user("someone", is_staff=is_staff, is_superuser=is_superuser)

    response = oidc_callback(client, user)

    if allowed:
        assert_logged_in(client, response, user, "byro.common.login.oidc")
    else:
        assert_rejected(client, response, user)


@pytest.mark.django_db
def test_wrong_password_is_not_reported_as_missing_access(client, create_user):
    user = create_user("someone")

    response = client.post(
        reverse("common:login"),
        {"username": user.username, "password": "wrong"},
        follow=True,
    )

    assert NO_ACCESS_MESSAGE not in response.content.decode()
    assert not LogEntry.objects.filter(action_type=NO_ACCESS).exists()


@pytest.mark.parametrize("was_superuser", (True, False))
@pytest.mark.django_db
def test_session_ends_when_backend_access_is_removed(
    client, create_user, configuration, login_user, was_superuser
):
    user = create_user("someone", is_staff=True, is_superuser=was_superuser)
    login_user(client, user)
    assert client.get(reverse("office:dashboard")).status_code == 200
    logouts = LogEntry.objects.filter(action_type="byro.common.logout")
    assert logouts.count() == 0

    user.is_staff = False
    user.is_superuser = False
    user.save()

    response = client.get(reverse("office:members.list"))
    assert response.status_code == 302
    assert response.url == reverse("common:login")
    assert SESSION_KEY not in client.session
    # the forced logout is recorded exactly like a regular one
    assert logouts.count() == 1
    assert logouts.get().user == user

    response = client.get(response.url)
    assert NO_ACCESS_MESSAGE in response.content.decode()

    # from here on the browser is anonymous, nothing else is logged
    response = client.get(reverse("office:members.list"))
    assert response.status_code == 302
    assert response.url == reverse("common:login") + "?next=/members/list"
    assert logouts.count() == 1


@pytest.mark.django_db
def test_removing_only_staff_keeps_a_superuser_logged_in(
    client, superuser, configuration, login_user
):
    login_user(client, superuser)
    superuser.is_staff = False
    superuser.save()

    assert client.get(reverse("office:dashboard")).status_code == 200
    assert client.session[SESSION_KEY] == str(superuser.pk)


@pytest.mark.django_db
def test_public_urls_stay_reachable_without_backend_access(
    client, create_user, configuration, login_user
):
    user = create_user("someone", is_staff=True)
    login_user(client, user)
    user.is_staff = False
    user.save()

    for name in ("common:log.info", "common:healthz", "common:login"):
        assert client.get(reverse(name)).status_code == 200, name
    assert not LogEntry.objects.filter(action_type="byro.common.logout").exists()


@pytest.mark.django_db
def test_logout_view_still_logs_and_ends_the_session(
    logged_in_client, configuration, user
):
    response = logged_in_client.get(reverse("common:logout"))

    assert response.status_code == 302
    assert SESSION_KEY not in logged_in_client.session
    entry = LogEntry.objects.get(action_type="byro.common.logout")
    assert entry.user == user


@pytest.mark.django_db
def test_logout_view_without_session_writes_no_log_entry(client):
    response = client.get(reverse("common:logout"))

    assert response.status_code == 302
    assert not LogEntry.objects.filter(action_type="byro.common.logout").exists()
