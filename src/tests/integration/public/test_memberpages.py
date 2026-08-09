import pytest
from django.urls import reverse


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
    assert any(
        s in response.content.decode() for s in ["Member page", "Mitgliedsseite"]
    )
    assert all(
        s not in response.content.decode() for s in ["Settings", "Einstellungen"]
    )


@pytest.mark.django_db
def test_memberpage_access_list(member, membership, client, configuration):
    response = client.get(
        reverse(
            "public:memberpage:member.list",
            kwargs={"secret_token": member.profile_memberpage.secret_token},
        )
    )
    assert response.status_code == 200
    assert any(
        s in response.content.decode() for s in ["Member page", "Mitgliedsseite"]
    )
    assert all(
        s not in response.content.decode() for s in ["Settings", "Einstellungen"]
    )


@pytest.mark.django_db
def test_memberlist_hides_inactive_members(
    member, membership, inactive_member, client, configuration
):
    # Both members consent to sharing, but only the active one may be listed.
    for m in (member, inactive_member):
        m.profile_memberpage.is_visible_to_members = True
        m.profile_memberpage.save()

    response = client.get(
        reverse(
            "public:memberpage:member.list",
            kwargs={"secret_token": member.profile_memberpage.secret_token},
        )
    )
    content = response.content.decode()
    assert response.status_code == 200
    assert member.name in content
    assert inactive_member.name not in content


@pytest.mark.parametrize("page", ("list", "dashboard"))
@pytest.mark.django_db
def test_memberpage_access_dashboard_wrong_token(
    member, membership, client, configuration, page
):
    response = client.get(
        reverse(
            f"public:memberpage:member.{page}",
            kwargs={"secret_token": member.profile_memberpage.secret_token + "lol"},
        )
    )
    assert response.status_code == 404
