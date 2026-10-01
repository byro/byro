import pytest
from django.contrib.auth import get_user_model

from byro.common import oidc


@pytest.fixture
def oidc_settings(settings):
    settings.OIDC_USERNAME_FIELD = "preferred_username"
    settings.OIDC_ADMIN_GROUP = ""
    settings.OIDC_AUTO_CREATE_ACCOUNT = True
    return settings


@pytest.fixture(autouse=True)
def no_userinfo_request(monkeypatch):
    def fail(access_token):
        raise AssertionError("unexpected userinfo request")

    monkeypatch.setattr(oidc, "get_userinfo", fail)


@pytest.mark.django_db
def test_auto_created_account_gets_backend_access_but_no_superuser(oidc_settings):
    user = oidc.get_or_create_user({"preferred_username": "newcomer"}, "token")

    user.refresh_from_db()
    assert user.username == "newcomer"
    assert user.is_staff
    assert not user.is_superuser
    assert user.is_active
    assert not user.has_usable_password()


@pytest.mark.parametrize(
    "is_staff,is_superuser",
    ((False, False), (True, False), (False, True), (True, True)),
)
@pytest.mark.django_db
def test_existing_account_is_never_changed(oidc_settings, is_staff, is_superuser):
    existing = get_user_model().objects.create(
        username="known", is_staff=is_staff, is_superuser=is_superuser
    )

    user = oidc.get_or_create_user(
        {"preferred_username": "known", "groups": ["anything"]}, "token"
    )

    assert user.pk == existing.pk
    user.refresh_from_db()
    assert user.is_staff is is_staff
    assert user.is_superuser is is_superuser


@pytest.mark.django_db
def test_admin_group_is_checked_before_an_account_is_created(oidc_settings):
    oidc_settings.OIDC_ADMIN_GROUP = "byro-admins"

    with pytest.raises(oidc.OIDCError):
        oidc.get_or_create_user(
            {"preferred_username": "outsider", "groups": ["other"]}, "token"
        )
    assert not get_user_model().objects.filter(username="outsider").exists()

    user = oidc.get_or_create_user(
        {"preferred_username": "insider", "groups": ["byro-admins"]}, "token"
    )
    assert user.is_staff
    assert not user.is_superuser


@pytest.mark.django_db
def test_no_account_is_created_without_auto_creation(oidc_settings):
    oidc_settings.OIDC_AUTO_CREATE_ACCOUNT = False

    with pytest.raises(oidc.OIDCError):
        oidc.get_or_create_user({"preferred_username": "newcomer"}, "token")
    assert not get_user_model().objects.filter(username="newcomer").exists()
