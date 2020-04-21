from django.urls import reverse

import pytest


@pytest.mark.django_db
def test_memberpage_access_dashboard(member, membership, client, configuration):
    response = client.get(
        reverse(
            "public:memberpage:member.dashboard",
            kwargs={"secret_token": member.profile_memberpage.secret_token},
        )
    )
    assert response.status_code == 200
    assert member.name in response.content.decode()
    assert "Member page" in response.content.decode()
    assert "Settings" not in response.content.decode()


@pytest.mark.django_db
def test_memberpage_access_list(member, membership, client, configuration):
    response = client.get(
        reverse(
            "public:memberpage:member.list",
            kwargs={"secret_token": member.profile_memberpage.secret_token},
        )
    )
    assert response.status_code == 200
    assert "Member page" in response.content.decode()
    assert "Settings" not in response.content.decode()


@pytest.mark.parametrize("page", ("list", "dashboard"))
@pytest.mark.django_db
def test_memberpage_access_dashboard_wrong_token(
    member, membership, client, configuration, page
):
    response = client.get(
        reverse(
            "public:memberpage:member.{}".format(page),
            kwargs={"secret_token": member.profile_memberpage.secret_token + "lol"},
        )
    )
    assert response.status_code == 404
