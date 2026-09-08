import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


def api_client_for(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.mark.django_db
def test_staff_user_can_use_api(user):
    assert user.is_staff
    assert not user.is_superuser
    response = api_client_for(user).get("/api/v1/members/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_superuser_without_staff_can_use_api():
    superuser = get_user_model().objects.create(
        username="super_no_staff", is_staff=False, is_superuser=True
    )
    response = api_client_for(superuser).get("/api/v1/members/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_user_without_staff_or_superuser_cannot_use_api():
    plain = get_user_model().objects.create(
        username="plain_user", is_staff=False, is_superuser=False
    )
    response = api_client_for(plain).get("/api/v1/members/")
    assert response.status_code == 403
