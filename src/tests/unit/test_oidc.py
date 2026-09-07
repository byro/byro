import pytest
from django.contrib.auth import get_user_model

from byro.common.oidc import OIDCError, get_or_create_user


@pytest.mark.django_db
def test_new_account_created_as_staff_without_group_config(settings):
    settings.OIDC_ADMIN_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = ""
    settings.OIDC_AUTO_CREATE_ACCOUNT = True

    user = get_or_create_user({"preferred_username": "new_user"}, "at")

    assert user.is_staff
    assert not user.is_superuser
    assert not user.has_usable_password()


@pytest.mark.django_db
def test_new_account_gets_superuser_when_in_superuser_group(settings):
    settings.OIDC_ADMIN_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = "byro-superadmins"
    settings.OIDC_AUTO_CREATE_ACCOUNT = True

    user = get_or_create_user(
        {"preferred_username": "new_admin", "groups": ["byro-superadmins"]}, "at"
    )

    assert user.is_staff
    assert user.is_superuser


@pytest.mark.django_db
def test_new_account_not_superuser_when_not_in_superuser_group(settings):
    settings.OIDC_ADMIN_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = "byro-superadmins"
    settings.OIDC_AUTO_CREATE_ACCOUNT = True

    user = get_or_create_user(
        {"preferred_username": "new_user", "groups": ["someone-else"]}, "at"
    )

    assert user.is_staff
    assert not user.is_superuser


@pytest.mark.django_db
def test_admin_group_required_to_create_or_log_in(settings):
    settings.OIDC_ADMIN_GROUP = "byro-admins"
    settings.OIDC_SUPERUSER_GROUP = ""
    settings.OIDC_AUTO_CREATE_ACCOUNT = True

    with pytest.raises(OIDCError):
        get_or_create_user(
            {"preferred_username": "outsider", "groups": ["someone-else"]}, "at"
        )
    assert not get_user_model().objects.filter(username="outsider").exists()


@pytest.mark.django_db
def test_existing_account_not_touched_without_sync(settings, user):
    settings.OIDC_ADMIN_GROUP = "byro-admins"
    settings.OIDC_SUPERUSER_GROUP = "byro-superadmins"
    settings.OIDC_SYNC_GROUPS = False
    user.is_staff = True
    user.is_superuser = True
    user.save()

    # Passes the admin_group login gate, but is no longer in superuser_group --
    # without sync, that must not touch the locally granted superuser status.
    result = get_or_create_user(
        {"preferred_username": user.username, "groups": ["byro-admins"]}, "at"
    )

    result.refresh_from_db()
    assert result.is_staff
    assert result.is_superuser


@pytest.mark.django_db
def test_existing_account_loses_superuser_when_synced_and_group_gone(settings, user):
    settings.OIDC_ADMIN_GROUP = "byro-admins"
    settings.OIDC_SUPERUSER_GROUP = "byro-superadmins"
    settings.OIDC_SYNC_GROUPS = True
    user.is_staff = True
    user.is_superuser = True
    user.save()

    result = get_or_create_user(
        {"preferred_username": user.username, "groups": ["byro-admins"]}, "at"
    )

    assert result.is_staff
    assert not result.is_superuser


@pytest.mark.django_db
def test_existing_account_gains_superuser_when_synced_and_group_present(settings, user):
    settings.OIDC_ADMIN_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = "byro-superadmins"
    settings.OIDC_SYNC_GROUPS = True
    user.is_superuser = False
    user.save()

    result = get_or_create_user(
        {"preferred_username": user.username, "groups": ["byro-superadmins"]}, "at"
    )

    assert result.is_superuser


@pytest.mark.django_db
def test_sync_does_not_touch_superuser_when_group_not_configured(settings, user):
    settings.OIDC_ADMIN_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = ""
    settings.OIDC_SYNC_GROUPS = True
    user.is_superuser = True
    user.save()

    result = get_or_create_user(
        {"preferred_username": user.username, "groups": []}, "at"
    )

    assert result.is_superuser


@pytest.mark.django_db
def test_sync_does_not_revoke_staff_when_admin_group_not_configured(settings, user):
    settings.OIDC_ADMIN_GROUP = ""
    settings.OIDC_SUPERUSER_GROUP = ""
    settings.OIDC_SYNC_GROUPS = True
    user.is_staff = True
    user.save()

    result = get_or_create_user(
        {"preferred_username": user.username, "groups": []}, "at"
    )

    assert result.is_staff
