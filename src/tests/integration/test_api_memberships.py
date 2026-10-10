import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from byro.members.models import FeeIntervals, Member

UNKNOWN_MEMBER_PK = 424242

VALID_MEMBERSHIP = {
    "start": "2024-01-01",
    "end": "2024-12-31",
    "amount": "20.00",
    "interval": FeeIntervals.MONTHLY,
}

INVALID_MEMBERSHIP = {"amount": "not a number"}


def api_client_for(user):
    token = Token.objects.create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def api(create_user):
    return api_client_for(create_user("api_user", is_staff=True))


def membership_url(member_pk, membership_pk=None):
    if membership_pk is None:
        return reverse("api:member-memberships-list", kwargs={"member_pk": member_pk})
    return reverse(
        "api:member-memberships-detail",
        kwargs={"member_pk": member_pk, "pk": membership_pk},
    )


@pytest.mark.django_db
def test_list_of_unknown_member_is_not_found(api):
    response = api.get(membership_url(UNKNOWN_MEMBER_PK))
    assert response.status_code == 404


@pytest.mark.django_db
def test_list_of_member_without_memberships_is_empty(api, member):
    response = api.get(membership_url(member.pk))
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_detail_of_unknown_member_is_not_found(api, membership):
    response = api.get(membership_url(UNKNOWN_MEMBER_PK, membership.pk))
    assert response.status_code == 404


@pytest.mark.django_db
def test_membership_of_another_member_is_not_found(api, membership):
    """The membership of a known member is not reachable through the URL of
    another member."""
    other = Member.objects.create(email="other@example.org", name="Other Member")
    old_amount = membership.amount
    for method, payload in (
        ("get", None),
        ("patch", {"amount": "99.00"}),
        ("delete", None),
    ):
        response = getattr(api, method)(
            membership_url(other.pk, membership.pk), payload, format="json"
        )
        assert response.status_code == 404, method
    membership.refresh_from_db()
    assert membership.amount == old_amount


@pytest.mark.django_db
def test_create_for_unknown_member_is_not_found(api):
    response = api.post(
        membership_url(UNKNOWN_MEMBER_PK), VALID_MEMBERSHIP, format="json"
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_create_for_unknown_member_is_not_found_before_body_validation(api):
    """The member is looked up before the body is validated, so an unknown
    member answers 404 and not 400 for a body it would never accept."""
    response = api.post(
        membership_url(UNKNOWN_MEMBER_PK), INVALID_MEMBERSHIP, format="json"
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_create_for_member_works(api, member):
    response = api.post(membership_url(member.pk), VALID_MEMBERSHIP, format="json")
    assert response.status_code == 201
    assert list(member.memberships.all()) == [
        member.memberships.get(pk=response.json()["id"])
    ]


@pytest.mark.django_db
def test_create_with_invalid_body_of_known_member_is_bad_request(api, member):
    response = api.post(membership_url(member.pk), INVALID_MEMBERSHIP, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_unknown_member_does_not_leak_through_permissions(create_user):
    """Authentication and permission are checked before the member is looked
    up, so 403 does not reveal whether a member exists."""
    client = api_client_for(create_user("api_user"))
    assert client.get(membership_url(UNKNOWN_MEMBER_PK)).status_code == 403
    assert client.get(membership_url(1)).status_code == 403


@pytest.mark.django_db
def test_unknown_member_requires_a_token():
    response = APIClient().get(membership_url(UNKNOWN_MEMBER_PK))
    assert response.status_code == 401
