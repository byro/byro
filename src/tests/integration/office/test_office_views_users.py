"""User management: reserved for superusers, except for the own profile."""

import pytest
from django.contrib.auth import get_user_model
from django.shortcuts import reverse

from byro.common.models import LogEntry

pytestmark = pytest.mark.usefixtures("configuration")

User = get_user_model()


def detail_url(user):
    return reverse("office:settings.users.detail", kwargs={"pk": user.pk})


def disable_password_url(user):
    return reverse("office:settings.users.disable-password", kwargs={"pk": user.pk})


def flags(user):
    user.refresh_from_db()
    return user.is_staff, user.is_superuser


# -- superusers --------------------------------------------------------------


@pytest.mark.django_db
def test_superuser_sees_user_list(superuser_client, superuser, user):
    response = superuser_client.get(reverse("office:settings.users.list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert user.username in content
    assert superuser.username in content


@pytest.mark.django_db
def test_new_users_get_backend_access_by_default(superuser_client):
    response = superuser_client.get(reverse("office:settings.users.add"))

    form = response.context["form"]
    assert form["is_staff"].value() is True
    assert form["is_superuser"].value() is False
    content = response.content.decode()
    assert "Allows this account to log in to the backend" in content
    # Django's default help text refers to an admin site byro does not have
    assert "admin site" not in content


@pytest.mark.parametrize(
    "posted,expected",
    (
        ({"is_staff": "on"}, (True, False)),
        ({}, (False, False)),
        ({"is_superuser": "on"}, (False, True)),
        ({"is_staff": "on", "is_superuser": "on"}, (True, True)),
    ),
)
@pytest.mark.django_db
def test_superuser_creates_users_with_any_flags(
    superuser_client, superuser, posted, expected
):
    response = superuser_client.post(
        reverse("office:settings.users.add"),
        {"username": "newbie", "password": "a-new-password", **posted},
    )

    new_user = User.objects.get(username="newbie")
    assert response.status_code == 302
    assert response.url == detail_url(new_user)
    assert flags(new_user) == expected
    assert new_user.check_password("a-new-password")
    assert LogEntry.objects.filter(
        action_type="byro.common.user.created", user=superuser
    ).exists()


@pytest.mark.parametrize("posted", ({}, {"password": ""}))
@pytest.mark.django_db
def test_creating_users_requires_a_password(superuser_client, superuser, posted):
    response = superuser_client.post(
        reverse("office:settings.users.add"),
        {"username": "newbie", "is_staff": "on", **posted},
    )

    assert response.status_code == 200
    assert "password" in response.context["form"].errors
    assert not User.objects.filter(username="newbie").exists()
    assert not LogEntry.objects.filter(
        action_type="byro.common.user.created", user=superuser
    ).exists()


@pytest.mark.django_db
def test_password_is_only_required_for_new_users(superuser_client, user):
    response = superuser_client.get(reverse("office:settings.users.add"))
    assert response.context["form"].fields["password"].required
    content = response.content.decode()
    # keeps password managers from filling in the credentials of the editor
    assert 'autocomplete="new-password"' in content
    assert "Leave empty to leave the password unchanged." not in content

    response = superuser_client.get(detail_url(user))
    assert not response.context["form"].fields["password"].required
    content = response.content.decode()
    assert 'autocomplete="new-password"' in content
    assert "Leave empty to leave the password unchanged." in content


@pytest.mark.parametrize("posted", ({}, {"password": ""}))
@pytest.mark.django_db
def test_superuser_edits_user_without_changing_the_password(
    superuser_client, superuser, user, posted
):
    password_hash = user.password

    response = superuser_client.post(
        detail_url(user),
        {
            "username": user.username,
            "last_name": "New Name",
            "email": "new@example.com",
            "is_superuser": "on",
            **posted,
        },
    )

    assert response.status_code == 302
    assert flags(user) == (False, True)
    assert user.last_name == "New Name"
    assert user.email == "new@example.com"
    assert user.password == password_hash
    assert user.check_password("test_password")
    assert LogEntry.objects.filter(
        action_type="byro.common.user.updated", user=superuser
    ).exists()


@pytest.mark.django_db
def test_superuser_sets_new_password_of_other_users(superuser_client, user):
    password_hash = user.password

    response = superuser_client.post(
        detail_url(user),
        {"username": user.username, "is_staff": "on", "password": "a-new-password"},
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.password != password_hash
    assert user.check_password("a-new-password")
    assert not user.check_password("test_password")


@pytest.mark.django_db
def test_disabled_password_stays_disabled_without_new_password(superuser_client, user):
    user.set_unusable_password()
    user.save()
    password_hash = user.password

    response = superuser_client.post(
        detail_url(user),
        {"username": user.username, "last_name": "New Name", "is_staff": "on"},
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.last_name == "New Name"
    assert user.password == password_hash
    assert not user.has_usable_password()

    # entering a password is the documented way to re-enable password login
    response = superuser_client.post(
        detail_url(user),
        {"username": user.username, "is_staff": "on", "password": "a-new-password"},
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.has_usable_password()
    assert user.check_password("a-new-password")


@pytest.mark.django_db
def test_superuser_changes_flags_of_other_users(superuser_client, superuser, user):
    response = superuser_client.post(
        detail_url(user),
        {"username": user.username, "password": "pw", "is_superuser": "on"},
    )

    assert response.status_code == 302
    assert flags(user) == (False, True)
    assert LogEntry.objects.filter(
        action_type="byro.common.user.updated", user=superuser
    ).exists()

    superuser_client.post(
        detail_url(user), {"username": user.username, "password": "pw"}
    )
    assert flags(user) == (False, False)


@pytest.mark.django_db
def test_superuser_cannot_remove_own_superuser_status(superuser_client, superuser):
    response = superuser_client.get(detail_url(superuser))
    form = response.context["form"]
    assert form.fields["is_superuser"].disabled
    assert "You cannot change your own superuser status." in response.content.decode()

    # a submitted form without ``is_superuser`` would uncheck an enabled box
    response = superuser_client.post(
        detail_url(superuser),
        {"username": superuser.username, "password": "test_password", "is_staff": "on"},
    )

    assert response.status_code == 302
    assert flags(superuser) == (True, True)


@pytest.mark.django_db
def test_superuser_may_drop_own_staff_flag_and_keeps_access(
    superuser_client, superuser, login_user
):
    response = superuser_client.post(
        detail_url(superuser),
        {"username": superuser.username, "password": "test_password"},
    )

    assert response.status_code == 302
    assert flags(superuser) == (False, True)
    # saving the form sets a new password, which ends the old session
    login_user(superuser_client, superuser)
    assert (
        superuser_client.get(reverse("office:settings.users.list")).status_code == 200
    )


@pytest.mark.django_db
def test_superuser_without_staff_manages_users(client, create_user, login_user, user):
    login_user(client, create_user("root", is_superuser=True))

    assert client.get(reverse("office:settings.users.list")).status_code == 200
    assert client.get(detail_url(user)).status_code == 200
    response = client.post(disable_password_url(user))
    assert response.status_code == 302
    user.refresh_from_db()
    assert not user.has_usable_password()


@pytest.mark.django_db
def test_superuser_gets_404_for_unknown_user(superuser_client):
    response = superuser_client.get(
        reverse("office:settings.users.detail", kwargs={"pk": 987654})
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_superuser_disables_password_of_others_but_not_own(
    superuser_client, superuser, user
):
    response = superuser_client.post(disable_password_url(superuser))
    assert response.status_code == 302
    superuser.refresh_from_db()
    assert superuser.has_usable_password()

    response = superuser_client.post(disable_password_url(user))
    assert response.status_code == 302
    user.refresh_from_db()
    assert not user.has_usable_password()
    assert LogEntry.objects.filter(
        action_type="byro.common.user.password_disabled", user=superuser
    ).exists()


# -- staff -------------------------------------------------------------------


@pytest.mark.django_db
def test_staff_edits_own_profile(logged_in_client, user):
    response = logged_in_client.get(detail_url(user))
    assert response.status_code == 200
    form = response.context["form"]
    assert "is_staff" not in form.fields
    assert "is_superuser" not in form.fields
    content = response.content.decode()
    assert 'name="is_superuser"' not in content
    assert 'name="is_staff"' not in content

    response = logged_in_client.post(
        detail_url(user),
        {
            "username": user.username,
            "last_name": "New Name",
            "email": "new@example.com",
            "password": "another-password",
        },
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.last_name == "New Name"
    assert user.email == "new@example.com"
    assert user.check_password("another-password")
    assert flags(user) == (True, False)


@pytest.mark.django_db
def test_staff_edits_own_profile_without_changing_the_password(logged_in_client, user):
    password_hash = user.password

    response = logged_in_client.post(
        detail_url(user),
        {
            "username": user.username,
            "last_name": "New Name",
            "email": "new@example.com",
        },
    )

    assert response.status_code == 302
    assert flags(user) == (True, False)
    assert user.last_name == "New Name"
    assert user.email == "new@example.com"
    assert user.password == password_hash
    assert user.check_password("test_password")
    # the unchanged password keeps the own session alive
    assert logged_in_client.get(detail_url(user)).status_code == 200


@pytest.mark.django_db
def test_staff_cannot_promote_themselves(logged_in_client, user):
    response = logged_in_client.post(
        detail_url(user),
        {
            "username": user.username,
            "password": "test_password",
            "is_superuser": "on",
            "is_staff": "on",
        },
    )

    assert response.status_code == 302
    assert flags(user) == (True, False)


@pytest.mark.django_db
def test_staff_does_not_lose_staff_by_saving_own_profile(logged_in_client, user):
    # the form has no ``is_staff`` field, a missing checkbox must not clear it
    logged_in_client.post(
        detail_url(user), {"username": user.username, "password": "test_password"}
    )
    assert flags(user) == (True, False)


@pytest.mark.django_db
def test_staff_cannot_view_or_edit_other_users(logged_in_client, create_user):
    other = create_user("other", is_staff=True, last_name="Original")

    assert logged_in_client.get(detail_url(other)).status_code == 403
    response = logged_in_client.post(
        detail_url(other),
        {
            "username": "renamed",
            "last_name": "Changed",
            "password": "taken-over",
            "is_superuser": "on",
        },
    )

    assert response.status_code == 403
    other.refresh_from_db()
    assert other.username == "other"
    assert other.last_name == "Original"
    assert other.check_password("test_password")
    assert flags(other) == (True, False)
    assert not LogEntry.objects.filter(action_type="byro.common.user.updated").exists()


@pytest.mark.django_db
def test_staff_cannot_probe_for_existing_users(logged_in_client):
    response = logged_in_client.get(
        reverse("office:settings.users.detail", kwargs={"pk": 987654})
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_cannot_disable_passwords(logged_in_client, user, create_user):
    other = create_user("other", is_staff=True)

    for target in (other, user):
        response = logged_in_client.post(disable_password_url(target))
        assert response.status_code == 403
        target.refresh_from_db()
        assert target.has_usable_password()
    assert not LogEntry.objects.filter(
        action_type="byro.common.user.password_disabled"
    ).exists()


@pytest.mark.django_db
def test_staff_cannot_list_users(logged_in_client):
    assert (
        logged_in_client.get(reverse("office:settings.users.list")).status_code == 403
    )
