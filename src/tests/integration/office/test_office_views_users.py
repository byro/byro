import pytest
from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from rest_framework.authtoken.models import Token


@pytest.mark.django_db
def test_staff_user_cannot_grant_self_superuser(
    client, configuration, user, login_user
):
    login_user(client, user)
    assert not user.is_superuser

    response = client.post(
        reverse("office:settings.users.detail", kwargs={"pk": user.pk}),
        {
            "username": user.username,
            "last_name": "",
            "email": "",
            "password": "test_password",
            "is_superuser": "on",
            "is_staff": "on",
        },
        follow=True,
    )
    assert response.status_code == 200

    user.refresh_from_db()
    assert not user.is_superuser


@pytest.mark.django_db
def test_staff_user_can_edit_own_profile(client, configuration, user, login_user):
    login_user(client, user)

    response = client.post(
        reverse("office:settings.users.detail", kwargs={"pk": user.pk}),
        {
            "username": user.username,
            "last_name": "New Name",
            "email": "new@example.org",
            "password": "test_password",
        },
        follow=True,
    )
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.last_name == "New Name"
    assert user.email == "new@example.org"


@pytest.mark.django_db
def test_staff_user_cannot_view_or_edit_other_user(
    client, configuration, user, login_user
):
    other = get_user_model().objects.create(
        username="other_user", is_staff=True, last_name="Original"
    )
    login_user(client, user)

    response = client.get(
        reverse("office:settings.users.detail", kwargs={"pk": other.pk}),
        follow=True,
    )
    assert response.status_code == 200
    assert response.resolver_match.url_name == "settings.users.detail"
    assert response.resolver_match.kwargs["pk"] == user.pk

    response = client.post(
        reverse("office:settings.users.detail", kwargs={"pk": other.pk}),
        {
            "username": other.username,
            "last_name": "Hijacked",
            "email": "",
            "password": "test_password",
            "is_superuser": "on",
            "is_staff": "on",
        },
        follow=True,
    )
    assert response.status_code == 200

    other.refresh_from_db()
    assert other.last_name == "Original"
    assert not other.is_superuser


@pytest.mark.django_db
def test_staff_user_cannot_add_users(client, configuration, user, login_user):
    login_user(client, user)

    response = client.get(reverse("office:settings.users.add"), follow=True)
    assert response.status_code == 200
    assert response.resolver_match.url_name == "settings.users.list"

    response = client.post(
        reverse("office:settings.users.add"),
        {
            "username": "brand_new_user",
            "last_name": "",
            "email": "",
            "password": "test_password",
        },
        follow=True,
    )
    assert response.status_code == 200
    assert not get_user_model().objects.filter(username="brand_new_user").exists()


@pytest.mark.django_db
def test_superuser_can_add_user(client, configuration, superuser, login_user):
    login_user(client, superuser)

    response = client.post(
        reverse("office:settings.users.add"),
        {
            "username": "brand_new_user",
            "last_name": "",
            "email": "",
            "password": "test_password",
            "is_superuser": "on",
            "is_staff": "on",
        },
        follow=True,
    )
    assert response.status_code == 200

    new_user = get_user_model().objects.get(username="brand_new_user")
    assert new_user.is_superuser


@pytest.mark.django_db
def test_superuser_can_grant_superuser(
    client, configuration, user, superuser, login_user
):
    login_user(client, superuser)
    assert not user.is_superuser

    response = client.post(
        reverse("office:settings.users.detail", kwargs={"pk": user.pk}),
        {
            "username": user.username,
            "last_name": "",
            "email": "",
            "password": "test_password",
            "is_superuser": "on",
            "is_staff": "on",
        },
        follow=True,
    )
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.is_superuser


@pytest.mark.django_db
def test_disabling_password_revokes_api_token(
    client, configuration, user, superuser, login_user
):
    token = Token.objects.create(user=user)
    login_user(client, superuser)

    response = client.post(
        reverse("office:settings.users.disable-password", kwargs={"pk": user.pk}),
        follow=True,
    )
    assert response.status_code == 200

    user.refresh_from_db()
    assert not user.has_usable_password()
    assert not Token.objects.filter(pk=token.pk).exists()


@pytest.mark.django_db
def test_admin_can_regenerate_other_users_token(
    client, configuration, user, superuser, login_user
):
    old_token = Token.objects.create(user=user)
    login_user(client, superuser)

    response = client.post(
        reverse("office:settings.users.regenerate-token", kwargs={"pk": user.pk}),
        follow=True,
    )
    assert response.status_code == 200

    assert not Token.objects.filter(pk=old_token.pk).exists()
    assert Token.objects.filter(user=user).exists()
    assert Token.objects.get(user=user).key != old_token.key


@pytest.mark.django_db
def test_staff_user_cannot_disable_other_users_password(
    client, configuration, user, login_user
):
    other = get_user_model().objects.create(username="other_user", is_staff=True)
    other.set_password("test_password")
    other.save()
    login_user(client, user)

    response = client.post(
        reverse("office:settings.users.disable-password", kwargs={"pk": other.pk}),
        follow=True,
    )
    assert response.status_code == 200

    other.refresh_from_db()
    assert other.has_usable_password()


@pytest.mark.django_db
def test_staff_user_cannot_regenerate_other_users_token(
    client, configuration, user, login_user
):
    other = get_user_model().objects.create(username="other_user", is_staff=True)
    old_token = Token.objects.create(user=other)
    login_user(client, user)

    response = client.post(
        reverse("office:settings.users.regenerate-token", kwargs={"pk": other.pk}),
        follow=True,
    )
    assert response.status_code == 200

    assert Token.objects.filter(pk=old_token.pk).exists()


@pytest.mark.django_db
def test_staff_user_can_regenerate_own_token(client, configuration, user, login_user):
    old_token = Token.objects.create(user=user)
    login_user(client, user)

    response = client.post(
        reverse("office:settings.users.regenerate-token", kwargs={"pk": user.pk}),
        follow=True,
    )
    assert response.status_code == 200

    assert not Token.objects.filter(pk=old_token.pk).exists()
    assert Token.objects.filter(user=user).exists()
