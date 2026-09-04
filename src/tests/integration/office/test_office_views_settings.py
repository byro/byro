import pytest
from django.shortcuts import reverse

from byro.common.forms.registration import DEFAULT_FIELDS
from byro.common.models import Configuration, LogEntry

REGISTRATION_CHANGED = "byro.settings.registration.changed"


def positions(*keys):
    return {f"{key}__position": str(index + 1) for index, key in enumerate(keys)}


@pytest.mark.django_db
def test_registration_settings_preselect_default_fields(
    configuration, logged_in_client
):
    response = logged_in_client.get(reverse("office:settings.registration"))
    content = response.content.decode()

    assert response.status_code == 200
    assert 'name="membership__start__position" value="5"' in content
    assert 'name="membership__end__position"' in content
    assert 'name="membership__end__position" value=' not in content
    assert content.count('class="card fancy-entry my-2 mandatory-entry"') == 3


@pytest.mark.django_db
def test_registration_settings_reject_missing_mandatory_fields(
    configuration, logged_in_client
):
    response = logged_in_client.post(
        reverse("office:settings.registration"), positions("member__name")
    )

    assert response.status_code == 200
    assert "alert alert-danger" in response.content.decode()
    assert Configuration.get_solo().registration_form is None
    assert not LogEntry.objects.filter(action_type=REGISTRATION_CHANGED).exists()


@pytest.mark.django_db
def test_registration_settings_save_mandatory_fields(configuration, logged_in_client):
    response = logged_in_client.post(
        reverse("office:settings.registration"), positions(*DEFAULT_FIELDS)
    )

    assert response.status_code == 302
    assert response.url == reverse("office:settings.registration")
    saved = {entry["name"] for entry in Configuration.get_solo().registration_form}
    assert {"membership__start", "membership__interval", "membership__amount"} <= saved
    assert LogEntry.objects.filter(action_type=REGISTRATION_CHANGED).exists()
