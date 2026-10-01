import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

# (is_staff, is_superuser, may use the API)
FLAG_COMBINATIONS = (
    pytest.param(False, False, False, id="no-flags"),
    pytest.param(True, False, True, id="staff"),
    pytest.param(False, True, True, id="superuser-without-staff"),
    pytest.param(True, True, True, id="staff-and-superuser"),
)


def api_client_for(user):
    token = Token.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.mark.parametrize("is_staff,is_superuser,allowed", FLAG_COMBINATIONS)
@pytest.mark.django_db
def test_api_read_access(create_user, member, is_staff, is_superuser, allowed):
    user = create_user("api_user", is_staff=is_staff, is_superuser=is_superuser)
    client = api_client_for(user)

    response = client.get(reverse("api:members-list"))
    assert response.status_code == (200 if allowed else 403)
    response = client.get(reverse("api:members-detail", kwargs={"pk": member.pk}))
    assert response.status_code == (200 if allowed else 403)


@pytest.mark.parametrize("is_staff,is_superuser,allowed", FLAG_COMBINATIONS)
@pytest.mark.django_db
def test_api_write_access(create_user, member, is_staff, is_superuser, allowed):
    user = create_user("api_user", is_staff=is_staff, is_superuser=is_superuser)
    old_name = member.name

    response = api_client_for(user).patch(
        reverse("api:members-detail", kwargs={"pk": member.pk}),
        {"name": "Changed Name"},
        format="json",
    )

    member.refresh_from_db()
    if allowed:
        assert response.status_code == 200
        assert member.name == "Changed Name"
    else:
        assert response.status_code == 403
        assert member.name == old_name


@pytest.mark.django_db
def test_api_rejects_inactive_superuser(create_user, member):
    user = create_user("api_user", is_staff=True, is_superuser=True, is_active=False)
    response = api_client_for(user).get(reverse("api:members-list"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_api_requires_a_token(member):
    response = APIClient().get(reverse("api:members-list"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_api_ignores_browser_session_of_a_superuser(
    superuser_client, configuration, member
):
    # the session is not an API credential, whatever the flags of the account
    response = superuser_client.get(reverse("api:members-list"))
    assert response.status_code == 401


@pytest.mark.django_db
def test_api_schema_and_docs_stay_public():
    assert APIClient().get(reverse("api:schema")).status_code == 200
    assert APIClient().get(reverse("api:swagger-ui")).status_code == 200


@pytest.mark.parametrize("is_superuser", (False, True))
@pytest.mark.django_db
def test_api_token_stops_working_when_backend_access_is_removed(
    create_user, member, is_superuser
):
    user = create_user("api_user", is_staff=True, is_superuser=is_superuser)
    client = api_client_for(user)
    url = reverse("api:members-list")
    assert client.get(url).status_code == 200

    user.is_staff = False
    user.is_superuser = False
    user.save()

    # the very same token that worked a moment ago
    assert client.get(url).status_code == 403
    response = client.patch(
        reverse("api:members-detail", kwargs={"pk": member.pk}),
        {"name": "Changed Name"},
        format="json",
    )
    assert response.status_code == 403
    member.refresh_from_db()
    assert member.name != "Changed Name"

    # granting access again revives the token, it was never deleted
    user.is_staff = True
    user.save()
    assert client.get(url).status_code == 200
