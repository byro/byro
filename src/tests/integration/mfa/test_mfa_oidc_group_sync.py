"""The OIDC group synchronization must not change how MFA treats an OIDC
login. Everything runs through the real callback, account lookup and
synchronization; only the identity provider is replaced."""

import pytest
from django.contrib.auth import SESSION_KEY
from django.urls import reverse

from byro.common.models import LogEntry
from byro.mfa.models import MFAConfiguration

STAFF_GROUP = "byro-staff"
SUPERUSER_GROUP = "byro-superusers"
SYNCED = "byro.common.user.oidc_permissions_synced"


@pytest.fixture
def synced_login(oidc_provider, settings):
    settings.OIDC_STAFF_GROUP = STAFF_GROUP
    settings.OIDC_SUPERUSER_GROUP = SUPERUSER_GROUP
    settings.OIDC_SYNC_GROUPS = True

    def login(client, username, groups):
        return oidc_provider(client, {"preferred_username": username, "groups": groups})

    return login


@pytest.fixture
def except_oidc_policy(configuration):
    config = MFAConfiguration.get_solo()
    config.policy = MFAConfiguration.Policy.REQUIRED_EXCEPT_OIDC
    config.save()
    return config


def flags_of(account):
    account.refresh_from_db()
    return account.is_staff, account.is_superuser


def assert_roles_were_synced(account, expected):
    assert flags_of(account) == expected
    assert LogEntry.objects.filter(action_type=SYNCED).count() == 1


@pytest.mark.parametrize(
    "groups,expected",
    (([STAFF_GROUP], (True, False)), ([SUPERUSER_GROUP], (False, True))),
)
@pytest.mark.django_db
def test_required_policy_applies_to_a_synchronized_oidc_login(
    client, create_user, mfa_policy, synced_login, groups, expected
):
    account = create_user("known")

    response = synced_login(client, "known", groups)

    assert_roles_were_synced(account, expected)
    assert response.status_code == 302
    assert response.url == "/"
    assert client.session[SESSION_KEY] == str(account.pk)
    # logged in, but the policy still demands the enrollment
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))


@pytest.mark.django_db
def test_required_policy_applies_to_a_newly_provisioned_account(
    client, mfa_policy, synced_login
):
    response = synced_login(client, "newcomer", [STAFF_GROUP])

    assert response.url == "/"
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))


@pytest.mark.django_db
def test_oidc_exception_policy_still_exempts_a_synchronized_oidc_login(
    client, create_user, except_oidc_policy, synced_login
):
    account = create_user("known")

    response = synced_login(client, "known", [STAFF_GROUP])

    assert_roles_were_synced(account, (True, False))
    assert response.url == "/"
    assert client.get(reverse("office:dashboard")).status_code == 200

    # the exemption belongs to the OIDC session only: a password login of the
    # same account is subject to the policy again
    response = client.post(
        reverse("common:login"), {"username": "known", "password": "test_password"}
    )
    assert response.status_code == 302
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))


@pytest.mark.parametrize("policy", ("optional", "required", "required_except_oidc"))
@pytest.mark.django_db
def test_own_authenticator_is_always_required_after_a_synchronized_oidc_login(
    client, mfa_user, totp_device, configuration, synced_login, fresh_code, policy
):
    config = MFAConfiguration.get_solo()
    config.policy = policy
    config.save()

    # the synchronization changes both roles of the account during this login
    response = synced_login(client, mfa_user.username, [SUPERUSER_GROUP])

    assert_roles_were_synced(mfa_user, (False, True))
    assert response.url == "/"
    response = client.get(reverse("office:members.list"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))
    # the enrollment is no way around the challenge
    response = client.get(reverse("mfa:setup"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))

    client.post(reverse("mfa:challenge"), {"token": fresh_code(totp_device)})
    assert client.get(reverse("office:members.list")).status_code == 200
    assert client.get(reverse("office:settings.users.list")).status_code == 200


@pytest.mark.parametrize("policy", ("required", "required_except_oidc"))
@pytest.mark.django_db
def test_account_that_lost_its_roles_never_reaches_the_mfa_flow(
    client, mfa_user, totp_device, configuration, synced_login, policy
):
    config = MFAConfiguration.get_solo()
    config.policy = policy
    config.save()

    response = synced_login(client, mfa_user.username, [])

    assert_roles_were_synced(mfa_user, (False, False))
    assert response.status_code == 302
    assert response.url == reverse("common:login")
    assert SESSION_KEY not in client.session
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("common:login"))
