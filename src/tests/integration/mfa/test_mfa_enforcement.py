import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from byro.common.models import LogEntry
from byro.mfa import services
from byro.mfa.models import MFAConfiguration, TOTPDevice

SETTINGS_POST_DATA = {
    "Configuration-currency_symbol": "€",
    "Configuration-currency_postfix": "on",
    "Configuration-display_cents": "on",
    "Configuration-liability_interval": "36",
    "Configuration-default_order_name": "last",
    "Configuration-default_direct_address_name": "first",
    # PGPConfiguration is rendered on the same page; its required fields
    # must be present for the combined form to validate.
    "PGPConfiguration-missing_key_policy": "send_plain",
    "PGPConfiguration-invalid_key_policy": "block",
    "PGPConfiguration-unverified_key_policy": "block",
    "PGPConfiguration-expired_key_policy": "block",
    "PGPConfiguration-key_refresh_interval_days": "1",
    "PGPConfiguration-keyserver_timeout_seconds": "30",
    "PGPConfiguration-expiry_reminder_days": "30",
}


@pytest.mark.django_db
def test_policy_is_disabled_by_default(configuration):
    assert MFAConfiguration.get_solo().require_mfa is False
    assert not services.policy_requires_mfa()


@pytest.mark.django_db
def test_policy_can_be_changed_on_settings_page(logged_in_client, configuration):
    response = logged_in_client.get(reverse("office:settings.base"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Require MFA for all administrators" in content
    assert 'name="MFAConfiguration-require_mfa"' in content
    # heading in the label column next to the checkbox
    assert "Mandatory MFA" in content
    assert 'name="MFAConfiguration-issuer"' not in content
    assert 'name="MFAConfiguration-account_label"' in content
    assert 'value="{association} - {username}"' in content

    data = {
        **SETTINGS_POST_DATA,
        "Configuration-name": configuration.name,
        "Configuration-mail_from": configuration.mail_from,
        "Configuration-backoffice_mail": configuration.backoffice_mail,
        "MFAConfiguration-require_mfa": "on",
        "MFAConfiguration-account_label": "{username} ({email})",
    }
    response = logged_in_client.post(reverse("office:settings.base"), data)
    assert response.status_code == 302
    config = MFAConfiguration.get_solo()
    assert config.require_mfa is True
    assert config.account_label == "{username} ({email})"
    entry = LogEntry.objects.filter(action_type="byro.settings.changed").latest("pk")
    assert entry.content_object == config
    assert entry.data["changes"]["require_mfa"] == ["False", "True"]
    assert entry.data["changes"]["account_label"] == [
        "{association} - {username}",
        "{username} ({email})",
    ]


@pytest.mark.django_db
def test_settings_page_rejects_unknown_placeholder(logged_in_client, configuration):
    data = {
        **SETTINGS_POST_DATA,
        "Configuration-name": configuration.name,
        "Configuration-mail_from": configuration.mail_from,
        "Configuration-backoffice_mail": configuration.backoffice_mail,
        "MFAConfiguration-account_label": "{username} {typo}",
    }
    response = logged_in_client.post(reverse("office:settings.base"), data)
    assert response.status_code == 200
    assert "Unknown placeholder" in response.content.decode()
    assert MFAConfiguration.get_solo().account_label == "{association} - {username}"


@pytest.mark.django_db
def test_settings_page_rejects_colons(logged_in_client, configuration):
    data = {
        **SETTINGS_POST_DATA,
        "Configuration-name": configuration.name,
        "Configuration-mail_from": configuration.mail_from,
        "Configuration-backoffice_mail": configuration.backoffice_mail,
        "MFAConfiguration-account_label": "BYRO: {username}",
    }
    response = logged_in_client.post(reverse("office:settings.base"), data)
    assert response.status_code == 200
    assert "Colons are not allowed" in response.content.decode()
    assert MFAConfiguration.get_solo().account_label == "{association} - {username}"


@pytest.mark.django_db
def test_policy_forces_enrollment_after_login(client, user, mfa_policy, login_user):
    login_user(client, user)
    setup = reverse("mfa:setup")

    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url == setup + "?next=%2F"

    for name in (
        "office:members.list",
        "office:settings.base",
        "office:settings.users.list",
        "mfa:settings",
        "mfa:recovery-codes",
        "mfa:disable",
    ):
        response = client.get(reverse(name))
        assert response.status_code == 302, name
        assert response.url.startswith(setup), name

    # no device: the challenge sends the user to the enrollment as well
    response = client.get(reverse("mfa:challenge"))
    assert response.status_code == 302
    assert response.url.startswith(setup)

    # the enrollment itself and logout are reachable
    assert client.get(setup).status_code == 200
    response = client.get(reverse("common:logout"))
    assert response.status_code == 302
    assert client.get(reverse("common:login")).status_code == 200


@pytest.mark.django_db
def test_policy_enrollment_grants_access(
    client, user, mfa_policy, login_user, totp_code
):
    login_user(client, user)
    response = client.get(reverse("mfa:setup") + "?next=/members/list")
    assert response.status_code == 200
    content = response.content.decode()
    assert "required for all administrators" in content
    # reduced navigation while locked
    assert reverse("office:members.list") not in content.replace(
        'value="/members/list"', ""
    )

    device = TOTPDevice.objects.get(user=user)
    response = client.post(
        reverse("mfa:setup"),
        {"token": totp_code(device), "next": "/members/list"},
    )
    assert response.status_code == 200
    assert "now enabled" in response.content.decode()

    assert client.get(reverse("office:members.list")).status_code == 200
    assert client.get(reverse("office:dashboard")).status_code == 200


@pytest.mark.django_db
def test_policy_applies_to_existing_sessions(client, user, configuration, login_user):
    login_user(client, user)
    assert client.get(reverse("office:dashboard")).status_code == 200

    config = MFAConfiguration.get_solo()
    config.require_mfa = True
    config.save()

    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))


@pytest.mark.django_db
def test_policy_user_with_mfa_gets_challenge(
    client, mfa_user, totp_device, mfa_policy, login_user, fresh_code
):
    login_user(client, mfa_user)
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))

    # setup is not an alternative to the challenge for users with a device
    response = client.get(reverse("mfa:setup"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))

    client.post(reverse("mfa:challenge"), {"token": fresh_code(totp_device)})
    assert client.get(reverse("office:dashboard")).status_code == 200


@pytest.mark.django_db
def test_policy_applies_to_every_backend_user(client, mfa_policy, login_user):
    # byro's office does not use the staff flag; every user who can log in
    # has full access, so every user is covered by the policy.
    plain = get_user_model().objects.create(
        username="plain_user", is_staff=False, is_superuser=False
    )
    plain.set_password("test_password")
    plain.save()
    login_user(client, plain)
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))


@pytest.mark.django_db
def test_reset_does_not_bypass_policy(client, mfa_user, mfa_policy, login_user):
    call_command("mfa_reset", mfa_user.username, "--force")

    assert MFAConfiguration.get_solo().require_mfa is True
    login_user(client, mfa_user)
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))


@pytest.mark.django_db
def test_public_urls_are_not_affected_by_policy(client, mfa_policy):
    assert client.get(reverse("common:login")).status_code == 200
    assert client.get(reverse("common:log.info")).status_code == 200
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("common:login"))


@pytest.mark.django_db
def test_policy_with_incomplete_initial_settings_does_not_loop(
    client, user, login_user
):
    # Fresh installation: general settings incomplete, policy on, no device.
    config = MFAConfiguration.get_solo()
    config.require_mfa = True
    config.save()
    login_user(client, user)

    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:setup"))
    assert client.get(reverse("mfa:setup")).status_code == 200
    # once enrolled (simulated), the initial settings take over again
    device = TOTPDevice.objects.get(user=user)
    device.confirmed = True
    device.save()
    response = client.get(reverse("mfa:setup"), follow=False)
    assert response.status_code == 302
    assert response.url.startswith(reverse("mfa:challenge"))
