import pytest

from byro.common.checks import check_oidc_group_configuration


@pytest.fixture
def oidc_settings(settings):
    settings.OIDC_ADMIN_GROUP = ""
    settings.OIDC_STAFF_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = ""
    settings.OIDC_SYNC_GROUPS = False
    settings.OIDC_GROUP_CONFLICT = False
    return settings


def check_ids():
    messages = check_oidc_group_configuration(None)
    # Warnings never stop ``manage.py check``, so byro still starts and the
    # password login of a break-glass account stays available.
    assert all(not message.is_serious() for message in messages)
    return [message.id for message in messages]


def test_no_warning_without_oidc_groups(oidc_settings):
    assert check_ids() == []


def test_no_warning_for_current_options(oidc_settings):
    oidc_settings.OIDC_STAFF_GROUP = "byro-staff"
    oidc_settings.OIDC_SUPERUSER_GROUP = "byro-superusers"
    oidc_settings.OIDC_SYNC_GROUPS = True
    assert check_ids() == []


def test_admin_group_is_reported_as_deprecated(oidc_settings):
    oidc_settings.OIDC_ADMIN_GROUP = "byro-admins"
    oidc_settings.OIDC_STAFF_GROUP = "byro-admins"
    assert check_ids() == ["byro.common.W002"]


def test_conflicting_groups_are_reported(oidc_settings):
    oidc_settings.OIDC_ADMIN_GROUP = "byro-admins"
    oidc_settings.OIDC_GROUP_CONFLICT = True
    oidc_settings.OIDC_SYNC_GROUPS = True

    (message,) = check_oidc_group_configuration(None)
    assert message.id == "byro.common.W001"
    assert "OIDC login is disabled" in message.msg
    # the values themselves are configuration details and not repeated
    assert "byro-admins" not in message.msg


def test_sync_without_groups_is_reported(oidc_settings):
    oidc_settings.OIDC_SYNC_GROUPS = True
    assert check_ids() == ["byro.common.W003"]

    oidc_settings.OIDC_SUPERUSER_GROUP = "byro-superusers"
    assert check_ids() == []
