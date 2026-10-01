import pytest
from django.shortcuts import reverse


@pytest.mark.django_db
def test_office_dashboard_view_redirects_without_settings(logged_in_client, member):
    response = logged_in_client.get(reverse("office:dashboard"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_office_dashboard_view(logged_in_client, member, configuration):
    response = logged_in_client.get(reverse("office:dashboard"))
    assert response.status_code == 200


@pytest.fixture
def missing_signing_key():
    from byro.mails.models import PGPConfiguration

    config = PGPConfiguration.get_solo()
    config.signing_enabled = True
    config.signing_key_fingerprint = ""
    config.save()


def dashboard_blocks(client):
    response = client.get(reverse("office:dashboard"))
    assert response.status_code == 200
    content = response.content.decode()
    start = content.index('<div class="dashboard-list">')
    return content[start : content.index("<footer>", start)]


@pytest.mark.django_db
def test_staff_sees_pgp_signing_warning_without_settings_link(
    logged_in_client, configuration, missing_signing_key
):
    blocks = dashboard_blocks(logged_in_client)

    assert "PGP signing incomplete" in blocks
    assert "Signing is enabled, but no signing key is configured." in blocks
    assert "Please ask a superuser to configure it in the settings." in blocks
    assert '<div class="dashboard-block block-danger">' in blocks
    assert f'href="{reverse("office:settings.base")}"' not in blocks


@pytest.mark.parametrize("is_staff", (True, False))
@pytest.mark.django_db
def test_superuser_sees_pgp_signing_warning_with_settings_link(
    client, create_user, login_user, configuration, missing_signing_key, is_staff
):
    login_user(client, create_user("root", is_staff=is_staff, is_superuser=True))
    blocks = dashboard_blocks(client)

    assert "PGP signing incomplete" in blocks
    assert f'href="{reverse("office:settings.base")}"' in blocks
    assert "Please ask a superuser" not in blocks
    assert '<div class="dashboard-block block-danger">' not in blocks
