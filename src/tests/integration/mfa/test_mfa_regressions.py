"""Member pages, REST API and OIDC must behave exactly as before, no matter
what the MFA policy or the user's MFA state is."""

import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from byro.common import views as common_views
from byro.common.models import LogEntry

# -- member pages -----------------------------------------------------------


@pytest.mark.django_db
def test_memberpage_works_with_policy(member, membership, client, mfa_policy):
    token = member.profile_memberpage.secret_token
    for name in ("member.dashboard", "member.list"):
        response = client.get(
            reverse(f"public:memberpage:{name}", kwargs={"secret_token": token})
        )
        assert response.status_code == 200, name
        assert member.name in response.content.decode() or name == "member.list"
    response = client.get(
        reverse(
            "public:memberpage:member.dashboard",
            kwargs={"secret_token": token + "x"},
        )
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_memberpage_proposal_works_with_policy(member, membership, client, mfa_policy):
    token = member.profile_memberpage.secret_token
    response = client.post(
        reverse("public:memberpage:member.propose", kwargs={"secret_token": token}),
        {},
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "public:memberpage:member.dashboard", kwargs={"secret_token": token}
    )


@pytest.mark.django_db
def test_memberpage_works_for_unverified_admin_session(
    member, membership, client, mfa_user, mfa_policy, login_user
):
    login_user(client, mfa_user)
    assert client.get(reverse("office:dashboard")).status_code == 302
    response = client.get(
        reverse(
            "public:memberpage:member.dashboard",
            kwargs={"secret_token": member.profile_memberpage.secret_token},
        )
    )
    assert response.status_code == 200
    assert member.name in response.content.decode()


# -- REST API ---------------------------------------------------------------


@pytest.fixture
def api_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.mark.django_db
def test_api_token_works_with_policy_without_mfa(api_client, member, mfa_policy):
    response = api_client.get("/api/v1/members/")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    assert response.json()["count"] >= 1


@pytest.mark.django_db
def test_api_token_works_for_user_with_mfa(api_client, mfa_user, member, mfa_policy):
    response = api_client.get("/api/v1/members/")
    assert response.status_code == 200
    response = api_client.get(f"/api/v1/members/{member.pk}/")
    assert response.status_code == 200
    assert response.json()["name"] == member.name


@pytest.mark.django_db
def test_api_without_token_is_denied_not_redirected(mfa_policy, member):
    response = APIClient().get("/api/v1/members/")
    assert response.status_code == 401
    assert response["Content-Type"].startswith("application/json")


@pytest.mark.django_db
def test_api_ignores_unverified_browser_session(
    client, mfa_user, mfa_policy, member, login_user
):
    login_user(client, mfa_user)
    response = client.get("/api/v1/members/")
    # the session is not an API credential; no HTML redirect to the challenge
    assert response.status_code == 401
    assert response["Content-Type"].startswith("application/json")


@pytest.mark.django_db
def test_api_schema_and_docs_stay_public(mfa_policy):
    assert APIClient().get(reverse("api:schema")).status_code == 200
    assert APIClient().get(reverse("api:swagger-ui")).status_code == 200


# -- OIDC -------------------------------------------------------------------


@pytest.fixture
def oidc(monkeypatch, user):
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

    def callback(client, next_url=None):
        session = client.session
        session["oidc_state"] = "state123"
        session["oidc_nonce"] = "nonce123"
        session.save()
        url = reverse("common:oidc-callback") + "?state=state123&code=abc"
        if next_url:
            url += "&next=" + next_url
        return client.get(url)

    return callback


@pytest.mark.django_db
def test_oidc_login_without_mfa_is_unchanged(client, user, configuration, oidc):
    response = oidc(client, next_url="/members/list")
    assert response.status_code == 302
    assert response.url == "/members/list"
    assert client.get("/members/list").status_code == 200
    assert LogEntry.objects.filter(action_type="byro.common.login.oidc").exists()


@pytest.mark.django_db
def test_oidc_login_cannot_bypass_policy(client, user, mfa_policy, oidc):
    response = oidc(client)
    assert response.status_code == 302
    assert response.url == "/"
    response = client.get("/")
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))


@pytest.mark.django_db
def test_oidc_login_requires_challenge_for_mfa_user(
    client, mfa_user, totp_device, configuration, oidc, fresh_code
):
    response = oidc(client, next_url="/members/list")
    assert response.status_code == 302
    assert response.url == "/members/list"

    response = client.get("/members/list")
    assert response.status_code == 302
    assert response.url == reverse("mfa:challenge") + "?next=%2Fmembers%2Flist"

    response = client.post(
        reverse("mfa:challenge"),
        {"token": fresh_code(totp_device), "next": "/members/list"},
    )
    assert response.status_code == 302
    assert response.url == "/members/list"
    assert client.get("/members/list").status_code == 200


@pytest.mark.django_db
def test_oidc_login_does_not_inherit_verification(
    client, mfa_user, totp_device, configuration, oidc, fresh_code, login_user
):
    login_user(client, mfa_user)
    client.post(reverse("mfa:challenge"), {"token": fresh_code(totp_device)})
    assert client.get("/").status_code == 200

    # a new login in the same browser session starts unverified again
    oidc(client)
    response = client.get("/")
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))
