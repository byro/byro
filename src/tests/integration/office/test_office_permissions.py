"""Server-side enforcement of the permission model for every combination of
``is_staff`` and ``is_superuser``:

- no flag: no backend access
- staff: regular backend access
- superuser: additionally settings, registration form, user management, log
"""

import pytest
from django.contrib.auth import get_user_model
from django.shortcuts import reverse

from byro.common.forms.registration import DEFAULT_FIELDS
from byro.common.models import Configuration, LogEntry

# (is_staff, is_superuser, backend access, administrative access)
FLAG_COMBINATIONS = (
    pytest.param(False, False, False, False, id="no-flags"),
    pytest.param(True, False, True, False, id="staff"),
    pytest.param(False, True, True, True, id="superuser-without-staff"),
    pytest.param(True, True, True, True, id="staff-and-superuser"),
)

OPERATIONAL_URLS = (
    "office:dashboard",
    "office:members.list",
    "office:members.add",
    "office:members.typeahead",
    "office:finance.accounts.list",
    "office:finance.uploads.list",
    "office:mails.outbox.list",
    "office:mails.templates.list",
    "office:settings.about",
    "office:settings.api-token",
    "mfa:settings",
)

SUPERUSER_URLS = (
    "office:settings.initial",
    "office:settings.base",
    "office:settings.registration",
    "office:settings.log",
    "office:settings.users.list",
    "office:settings.users.add",
)


@pytest.fixture
def client_for(client, create_user, login_user, configuration):
    def get_client(is_staff, is_superuser):
        user = create_user("someone", is_staff=is_staff, is_superuser=is_superuser)
        login_user(client, user)
        client.user = user
        return client

    return get_client


def assert_sent_to_login(response):
    assert response.status_code == 302
    assert response.url.startswith(reverse("common:login"))


@pytest.mark.parametrize("url", OPERATIONAL_URLS)
@pytest.mark.parametrize("is_staff,is_superuser,backend,admin", FLAG_COMBINATIONS)
@pytest.mark.django_db
def test_operational_urls(client_for, url, is_staff, is_superuser, backend, admin):
    response = client_for(is_staff, is_superuser).get(reverse(url))

    if backend:
        assert response.status_code == 200
    else:
        assert_sent_to_login(response)


@pytest.mark.parametrize("url", SUPERUSER_URLS)
@pytest.mark.parametrize("is_staff,is_superuser,backend,admin", FLAG_COMBINATIONS)
@pytest.mark.django_db
def test_superuser_only_urls(client_for, url, is_staff, is_superuser, backend, admin):
    response = client_for(is_staff, is_superuser).get(reverse(url))

    if admin:
        assert response.status_code == 200
    elif backend:
        assert response.status_code == 403
    else:
        assert_sent_to_login(response)


@pytest.mark.parametrize("is_staff,is_superuser,backend,admin", FLAG_COMBINATIONS)
@pytest.mark.django_db
def test_own_profile(client_for, is_staff, is_superuser, backend, admin):
    client = client_for(is_staff, is_superuser)
    response = client.get(
        reverse("office:settings.users.detail", kwargs={"pk": client.user.pk})
    )

    if backend:
        assert response.status_code == 200
    else:
        assert_sent_to_login(response)


@pytest.mark.parametrize("is_staff,is_superuser,backend,admin", FLAG_COMBINATIONS)
@pytest.mark.django_db
def test_other_profile(client_for, create_user, is_staff, is_superuser, backend, admin):
    other = create_user("other", is_staff=True)
    response = client_for(is_staff, is_superuser).get(
        reverse("office:settings.users.detail", kwargs={"pk": other.pk})
    )

    if admin:
        assert response.status_code == 200
    elif backend:
        assert response.status_code == 403
    else:
        assert_sent_to_login(response)


@pytest.mark.django_db
def test_forbidden_page_explains_itself_and_keeps_the_navigation(
    logged_in_client, configuration
):
    response = logged_in_client.get(reverse("office:settings.base"))

    assert response.status_code == 403
    content = response.content.decode()
    assert "Permission denied" in content
    assert "restricted to superusers" in content
    assert f'href="{reverse("office:members.list")}"' in content


# -- staff cannot change anything through superuser-only views ---------------


@pytest.mark.django_db
def test_staff_cannot_change_general_settings(logged_in_client, configuration):
    response = logged_in_client.post(
        reverse("office:settings.base"),
        {
            "Configuration-name": "Hijacked",
            "Configuration-mail_from": "evil@example.com",
            "Configuration-backoffice_mail": "evil@example.com",
        },
    )

    assert response.status_code == 403
    config = Configuration.get_solo()
    assert config.name == "Association Name"
    assert config.mail_from == "associationname@example.com"
    assert not LogEntry.objects.filter(action_type="byro.settings.changed").exists()


@pytest.mark.django_db
def test_staff_cannot_change_registration_form(logged_in_client, configuration):
    data = {f"{key}__position": str(i + 1) for i, key in enumerate(DEFAULT_FIELDS)}
    response = logged_in_client.post(reverse("office:settings.registration"), data)

    assert response.status_code == 403
    assert Configuration.get_solo().registration_form is None
    assert not LogEntry.objects.filter(
        action_type="byro.settings.registration.changed"
    ).exists()


@pytest.mark.django_db
def test_staff_cannot_create_users(logged_in_client, configuration):
    response = logged_in_client.post(
        reverse("office:settings.users.add"),
        {"username": "sneaky", "password": "secret", "is_superuser": "on"},
    )

    assert response.status_code == 403
    assert not get_user_model().objects.filter(username="sneaky").exists()


@pytest.mark.django_db
def test_superuser_without_staff_can_change_settings(client_for):
    client = client_for(False, True)
    data = {f"{key}__position": str(i + 1) for i, key in enumerate(DEFAULT_FIELDS)}

    response = client.post(reverse("office:settings.registration"), data)

    assert response.status_code == 302
    assert Configuration.get_solo().registration_form
    assert LogEntry.objects.filter(
        action_type="byro.settings.registration.changed", user=client.user
    ).exists()


# -- initial setup -----------------------------------------------------------


@pytest.mark.django_db
def test_initial_setup_is_left_to_superusers(client, user, login_user):
    # no ``configuration`` fixture: the installation is not set up yet
    login_user(client, user)

    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url == reverse("office:settings.initial")

    response = client.get(response.url)
    assert response.status_code == 403
    assert "has to be completed by a superuser" in response.content.decode()

    response = client.post(
        reverse("office:settings.initial"),
        {
            "name": "Hijacked",
            "backoffice_mail": "evil@example.com",
            "mail_from": "evil@example.com",
        },
    )
    assert response.status_code == 403
    assert not Configuration.get_solo().name


@pytest.mark.parametrize("is_staff", (True, False))
@pytest.mark.django_db
def test_superuser_can_complete_initial_setup(
    client, create_user, login_user, is_staff
):
    login_user(client, create_user("root", is_staff=is_staff, is_superuser=True))

    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url == reverse("office:settings.initial")
    assert client.get(response.url).status_code == 200

    response = client.post(
        reverse("office:settings.initial"),
        {
            "name": "Association Name",
            "backoffice_mail": "office@example.com",
            "mail_from": "office@example.com",
        },
    )
    assert response.status_code == 302
    assert response.url == reverse("office:settings.registration")
    assert Configuration.get_solo().name == "Association Name"
