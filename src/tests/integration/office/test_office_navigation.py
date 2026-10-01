"""The sidebar mirrors the permission model: Settings (including plugin
entries registered for that section) is shown to superusers only, About is a
regular entry for every backend user."""

from contextlib import contextmanager

import pytest
from django.shortcuts import reverse

from byro.office.signals import nav_event

pytestmark = pytest.mark.usefixtures("configuration")

SUPERUSER_LINKS = (
    "office:settings.base",
    "office:settings.registration",
    "office:settings.users.list",
    "office:settings.log",
)
REGULAR_LINKS = (
    "office:members.list",
    "office:finance.accounts.list",
    "office:mails.outbox.list",
    "office:settings.about",
)


def href(name):
    return f'href="{reverse(name)}"'


@contextmanager
def plugin_nav_entries(*entries):
    def receiver(sender, **kwargs):
        return list(entries)

    nav_event.connect(receiver, dispatch_uid="test-nav-plugin")
    try:
        yield
    finally:
        nav_event.disconnect(receiver, dispatch_uid="test-nav-plugin")


def sidebar(client, url_name="office:dashboard"):
    response = client.get(reverse(url_name))
    assert response.status_code == 200
    content = response.content.decode()
    start = content.index('<nav class="nav flex-column sidebar">')
    return content[start : content.index("</nav>", start)]


@pytest.mark.django_db
def test_staff_navigation_has_no_settings(logged_in_client):
    nav = sidebar(logged_in_client)

    for name in REGULAR_LINKS:
        assert href(name) in nav, name
    for name in SUPERUSER_LINKS:
        assert href(name) not in nav, name
    assert 'id="collapseSettings"' not in nav


@pytest.mark.parametrize("is_staff", (True, False))
@pytest.mark.django_db
def test_superuser_navigation(client, create_user, login_user, is_staff):
    login_user(client, create_user("root", is_staff=is_staff, is_superuser=True))
    nav = sidebar(client)

    for name in REGULAR_LINKS + SUPERUSER_LINKS:
        assert href(name) in nav, name
    # Settings sits below Mails, About directly below the Settings menu
    mails = nav.index(href("office:mails.outbox.list"))
    settings = nav.index(href("office:settings.base"))
    log = nav.index(href("office:settings.log"))
    about = nav.index(href("office:settings.about"))
    assert mails < settings < log < about
    assert nav.count(href("office:settings.about")) == 1
    assert "</li>" not in nav[about:]


@pytest.mark.django_db
def test_about_is_a_regular_page_for_staff(logged_in_client):
    nav = sidebar(logged_in_client, "office:settings.about")
    assert f'class="nav-link active" {href("office:settings.about")}' in nav


@pytest.mark.django_db
def test_about_does_not_open_the_settings_menu(superuser_client):
    collapsed = 'class="collapse in" aria-expand="true" id="collapseSettings"'
    opened = 'class="collapse in show" aria-expand="true" id="collapseSettings"'

    assert collapsed in sidebar(superuser_client, "office:settings.about")
    assert opened in sidebar(superuser_client, "office:settings.base")
    assert opened in sidebar(superuser_client, "office:settings.log")


@pytest.mark.django_db
def test_plugin_settings_entries_are_shown_to_superusers_only(
    logged_in_client, create_user, login_user
):
    entries = (
        {"label": "Plugin settings", "url": "/plugin/settings", "section": "settings"},
        {"label": "Plugin finance", "url": "/plugin/finance", "section": "finance"},
        {"label": "Plugin page", "url": "/plugin/page"},
    )
    with plugin_nav_entries(*entries):
        nav = sidebar(logged_in_client)
        assert "Plugin settings" not in nav
        assert 'href="/plugin/settings"' not in nav
        assert "Plugin finance" in nav
        assert "Plugin page" in nav

        login_user(logged_in_client, create_user("root", is_superuser=True))
        nav = sidebar(logged_in_client)
        assert "Plugin settings" in nav
        assert "Plugin finance" in nav
        assert "Plugin page" in nav
        # still below Mails and above About
        assert (
            nav.index(href("office:mails.outbox.list"))
            < nav.index('href="/plugin/settings"')
            < nav.index(href("office:settings.about"))
        )


@pytest.mark.django_db
def test_user_menu_keeps_own_profile_for_staff(logged_in_client, user):
    content = logged_in_client.get(reverse("office:dashboard")).content.decode()

    profile = reverse("office:settings.users.detail", kwargs={"pk": user.pk})
    assert f'href="{profile}"' in content
    assert href("mfa:settings") in content
    assert href("office:settings.api-token") in content


@pytest.mark.django_db
def test_user_list_marks_accounts_without_backend_access(superuser_client, create_user):
    create_user("flagless")

    content = superuser_client.get(
        reverse("office:settings.users.list")
    ).content.decode()

    assert content.count("No backend access") == 2  # title and screen reader text
    assert "Frontend user" not in content
