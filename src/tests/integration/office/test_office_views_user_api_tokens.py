"""API tokens: every backend user manages their own token, superusers can
revoke the token of another account, and every change is recorded in the
audit log without the token."""

import json
import logging
import traceback

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import constants as message_levels
from django.core.management import call_command
from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.backends.base.base import BaseDatabaseWrapper
from django.shortcuts import reverse
from django.test import Client
from django.urls import resolve
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from byro.common import api_tokens
from byro.common.models import LogEntry
from byro.common.templatetags.log_entry import format_log_entry, format_log_source

pytestmark = pytest.mark.usefixtures("configuration")

User = get_user_model()

CREATED = "byro.common.user.api_token_created"
REGENERATED = "byro.common.user.api_token_regenerated"
REVOKED = "byro.common.user.api_token_revoked"

TOKEN_PAGE = "office:settings.api-token"
TOKEN_REGENERATE = "office:settings.api-token.regenerate"


def detail_url(user):
    return reverse("office:settings.users.detail", kwargs={"pk": user.pk})


def revoke_url(user):
    return reverse("office:settings.users.revoke-api-token", kwargs={"pk": user.pk})


def api_status(key):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
    return client.get(reverse("api:members-list")).status_code


def token_entries():
    return LogEntry.objects.filter(
        action_type__startswith="byro.common.user.api_token_"
    ).order_by("id")


def actions():
    return list(token_entries().values_list("action_type", flat=True))


def keys_of(user):
    return list(Token.objects.filter(user=user).values_list("key", flat=True))


def messages_of(response):
    return [(m.level, str(m)) for m in response.context["messages"]]


@pytest.fixture
def production_errors(settings, caplog):
    """Uncaught exceptions are handled the way a deployment does it: Django
    answers with an error page and logs the exception with its traceback to
    ``django.request``. Returns a callable that checks what was logged."""
    settings.DEBUG = False
    settings.DEBUG_PROPAGATE_EXCEPTIONS = False
    caplog.set_level(logging.DEBUG)

    def assert_only_controlled_error_logged(response, error, *secrets):
        assert response.status_code == 500
        (record,) = [
            r for r in caplog.records if r.name == "django.request" and r.exc_info
        ]
        exc = record.exc_info[1]
        # what reached Django is the fixed error of the token service ...
        assert type(exc) is error
        assert exc.args == (error.message,)
        # ... and nothing leads back to the exception that caused it
        assert exc.__cause__ is None
        assert exc.__context__ is None
        rendered = "".join(traceback.format_exception(exc))
        assert error.message in rendered
        formatter = logging.Formatter("%(name)s %(message)s")
        assert secrets
        for secret in secrets:
            assert secret not in response.content.decode()
            assert secret not in rendered
            assert secret not in caplog.text
            for logged in caplog.records:
                assert secret not in formatter.format(logged)
                assert secret not in str(vars(logged))
            # nor do the frames of the traceback hold it in a local variable
            for frame, _ in traceback.walk_tb(exc.__traceback__):
                if "/byro/" in frame.f_code.co_filename:
                    assert secret not in repr(frame.f_locals)

    return assert_only_controlled_error_logged


@pytest.fixture
def target(create_user):
    """Another account with a working API token."""
    target = create_user("target", is_staff=True, email="target@example.org")
    target.key = Token.objects.create(user=target).key
    return target


def assert_untouched(target):
    assert keys_of(target) == [target.key]
    assert api_status(target.key) == 200
    assert not token_entries().exists()


# -- superusers revoke the token of another account --------------------------


@pytest.mark.django_db
def test_superuser_revokes_token_of_another_user(superuser_client, superuser, target):
    assert api_status(target.key) == 200

    response = superuser_client.post(revoke_url(target), follow=True)

    assert response.redirect_chain == [(detail_url(target), 302)]
    # removed and not replaced, the issued token is dead at once
    assert keys_of(target) == []
    assert api_status(target.key) == 401
    level, message = messages_of(response)[0]
    assert level == message_levels.SUCCESS
    assert "The API token has been revoked and no longer works." in message
    assert "The user can obtain a new token from their API token page." in message
    assert message in response.content.decode()
    entry = token_entries().get()
    assert entry.action_type == REVOKED
    assert entry.content_object == target
    assert entry.user == superuser


@pytest.mark.django_db
def test_superuser_without_staff_revokes_token(client, create_user, login_user, target):
    root = create_user("root", is_superuser=True)
    login_user(client, root)

    response = client.post(revoke_url(target))

    assert response.status_code == 302
    assert keys_of(target) == []
    assert api_status(target.key) == 401
    assert token_entries().get().user == root


@pytest.mark.django_db
def test_revoking_without_a_token_changes_and_logs_nothing(
    superuser_client, superuser, target
):
    superuser_client.post(revoke_url(target), follow=True)
    assert actions() == [REVOKED]

    response = superuser_client.post(revoke_url(target), follow=True)

    assert response.redirect_chain == [(detail_url(target), 302)]
    assert messages_of(response) == [
        (message_levels.INFO, "This user has no API token.")
    ]
    assert keys_of(target) == []
    assert actions() == [REVOKED]


@pytest.mark.django_db
def test_revocation_only_changes_the_token_of_the_target(
    superuser_client, superuser, create_user, target
):
    bystander = create_user("bystander", is_staff=True)
    own_key = Token.objects.create(user=superuser).key
    bystander_key = Token.objects.create(user=bystander).key
    target_client = Client()
    target_client.post(
        reverse("common:login"), {"username": "target", "password": "test_password"}
    )
    assert target_client.get(reverse("office:dashboard")).status_code == 200
    fields = (
        "username",
        "last_name",
        "email",
        "password",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
    )
    before = User.objects.values(*fields).get(pk=target.pk)

    superuser_client.post(revoke_url(target))

    assert keys_of(target) == []
    assert keys_of(superuser) == [own_key]
    assert keys_of(bystander) == [bystander_key]
    assert api_status(own_key) == 200
    assert api_status(bystander_key) == 200
    # the account itself is exactly as before
    assert User.objects.values(*fields).get(pk=target.pk) == before
    target.refresh_from_db()
    assert target.check_password("test_password")
    # and its browser session is still valid
    assert target_client.get(reverse("office:dashboard")).status_code == 200


@pytest.mark.django_db
def test_revocation_keeps_passwordless_oidc_login_working(
    superuser_client, create_user, oidc_provider
):
    sso_user = create_user("sso_user", is_staff=True)
    sso_user.set_unusable_password()
    sso_user.save()
    Token.objects.create(user=sso_user)

    superuser_client.post(revoke_url(sso_user))

    sso_user.refresh_from_db()
    assert not sso_user.has_usable_password()
    browser = Client()
    response = oidc_provider(browser, {"preferred_username": "sso_user"})
    assert response.status_code == 302
    assert response.url == "/"
    assert browser.get(reverse("office:dashboard")).status_code == 200


@pytest.mark.django_db
def test_superuser_cannot_revoke_own_token_through_user_management(
    superuser_client, superuser
):
    key = Token.objects.create(user=superuser).key

    response = superuser_client.post(revoke_url(superuser), follow=True)

    # sent to the page that manages the own token
    assert response.redirect_chain == [(reverse(TOKEN_PAGE), 302)]
    assert messages_of(response) == [
        (message_levels.ERROR, "Use your own API token page to manage your token.")
    ]
    assert keys_of(superuser) == [key]
    assert api_status(key) == 200
    assert not token_entries().exists()


@pytest.mark.django_db
def test_superuser_gets_404_for_unknown_user(superuser_client):
    response = superuser_client.post(
        reverse("office:settings.users.revoke-api-token", kwargs={"pk": 987654})
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_revocation_needs_a_post_request(superuser_client, target):
    assert superuser_client.get(revoke_url(target)).status_code == 405
    assert_untouched(target)


@pytest.mark.django_db
def test_token_stays_revoked_if_the_audit_entry_fails(
    superuser_client, target, monkeypatch
):
    create_entry = LogEntry.objects.create

    def failing_create(*args, **kwargs):
        if kwargs["action_type"] == REVOKED:
            raise RuntimeError("audit log is not available")
        return create_entry(*args, **kwargs)

    monkeypatch.setattr(LogEntry.objects, "create", failing_create)

    response = superuser_client.post(revoke_url(target), follow=True)

    # no error page: the superuser is told what happened
    assert response.redirect_chain == [(detail_url(target), 302)]
    level, message = messages_of(response)[0]
    assert level == message_levels.WARNING
    assert "The API token has been revoked and no longer works" in message
    assert "the audit log entry could not be written" in message
    assert "The user can obtain a new token from their API token page." in message
    assert keys_of(target) == []
    assert api_status(target.key) == 401
    assert not token_entries().exists()


@pytest.mark.django_db(transaction=True)
def test_failed_revocation_is_not_reported_as_done(
    superuser_client, target, monkeypatch
):
    """The transaction cannot be committed: there is no confirmed result, so
    the superuser gets an error instead of a success or warning message. The
    page of the account shows what the state of the token is; here the
    database refused the commit, so it is still there."""

    real_commit = BaseDatabaseWrapper.commit
    write_entry = api_tokens._write_revocation_entry
    revoking = []

    def write_entry_before_failing_commit(*args, **kwargs):
        revoking.append(True)
        return write_entry(*args, **kwargs)

    def failing_commit(self):
        # only the transaction of the revocation, not those of the middlewares
        if revoking:
            revoking.clear()
            raise OperationalError("could not commit")
        return real_commit(self)

    monkeypatch.setattr(
        api_tokens, "_write_revocation_entry", write_entry_before_failing_commit
    )
    monkeypatch.setattr(BaseDatabaseWrapper, "commit", failing_commit)

    with pytest.raises(api_tokens.ApiTokenRevocationError):
        superuser_client.post(revoke_url(target))

    assert keys_of(target) == [target.key]
    assert api_status(target.key) == 200
    assert not token_entries().exists()
    # the test client keeps the exception of the failed request
    superuser_client.exc_info = None
    response = superuser_client.get(detail_url(target))
    assert messages_of(response) == []
    assert response.context["has_api_token"] is True


@pytest.mark.django_db
def test_superuser_is_warned_if_the_audit_entry_is_rolled_back_silently(
    superuser_client, target, monkeypatch
):
    """The entry is inserted, then its savepoint is marked for rollback
    without an error. That must not count as a written audit entry."""
    create_entry = LogEntry.objects.create
    inserted = []

    def create_and_mark_for_rollback(*args, **kwargs):
        entry = create_entry(*args, **kwargs)
        if kwargs["action_type"] == REVOKED:
            inserted.append(LogEntry.objects.filter(pk=entry.pk).exists())
            transaction.set_rollback(True)
        return entry

    monkeypatch.setattr(LogEntry.objects, "create", create_and_mark_for_rollback)

    response = superuser_client.post(revoke_url(target), follow=True)

    assert inserted == [True]
    assert response.redirect_chain == [(detail_url(target), 302)]
    assert [level for level, _ in messages_of(response)] == [message_levels.WARNING]
    message = messages_of(response)[0][1]
    assert "The API token has been revoked and no longer works" in message
    assert "the audit log entry could not be written" in message
    assert keys_of(target) == []
    assert api_status(target.key) == 401
    assert not token_entries().exists()


@pytest.mark.django_db(transaction=True)
def test_request_log_of_a_failed_revocation_never_contains_the_token(
    superuser_client, target, monkeypatch, production_errors
):
    """Every exception on the way quotes the token. Django logs what reaches
    it with message and traceback, so only the fixed error of the token
    service may reach it."""
    key = target.key
    create_entry = LogEntry.objects.create

    def failing_create(*args, **kwargs):
        if kwargs["action_type"] == REVOKED:
            raise RuntimeError(f"cannot write the audit entry for {key}")
        return create_entry(*args, **kwargs)

    def broken_rollback(self, sid):
        raise OperationalError(f"SAVEPOINT does not exist ({key})")

    superuser_client.raise_request_exception = False
    with monkeypatch.context() as patch:
        patch.setattr(LogEntry.objects, "create", failing_create)
        patch.setattr(BaseDatabaseWrapper, "savepoint_rollback", broken_rollback)
        response = superuser_client.post(revoke_url(target))

    production_errors(response, api_tokens.ApiTokenRevocationError, key)
    assert not token_entries().exists()


@pytest.mark.django_db(transaction=True)
def test_revocation_works_with_atomic_requests(superuser_client, target, monkeypatch):
    """The revocation commits on its own and refuses to run in a transaction
    of the caller, so the view must not be wrapped in one."""
    monkeypatch.setitem(connection.settings_dict, "ATOMIC_REQUESTS", True)
    view = resolve(revoke_url(target)).func
    assert view._non_atomic_requests == {"default"}

    response = superuser_client.post(revoke_url(target))

    assert response.status_code == 302
    assert response.url == detail_url(target)
    assert keys_of(target) == []
    assert api_status(target.key) == 401
    assert actions() == [REVOKED]


# -- nobody else can -----------------------------------------------------------


@pytest.mark.django_db
def test_staff_cannot_revoke_tokens(logged_in_client, user, target):
    own_key = Token.objects.create(user=user).key

    # another account, the own account, an account that does not exist
    for pk in (target.pk, user.pk, 987654):
        response = logged_in_client.post(
            reverse("office:settings.users.revoke-api-token", kwargs={"pk": pk})
        )
        assert response.status_code == 403

    assert keys_of(user) == [own_key]
    assert_untouched(target)


@pytest.mark.django_db
def test_staff_cannot_see_token_state_of_other_users(logged_in_client, target):
    assert logged_in_client.get(detail_url(target)).status_code == 403


@pytest.mark.django_db
def test_anonymous_cannot_revoke_tokens(client, target):
    response = client.post(revoke_url(target))

    assert response.status_code == 302
    assert response.url.startswith(reverse("common:login"))
    assert_untouched(target)


@pytest.mark.django_db
def test_account_without_backend_access_cannot_revoke_tokens(
    client, create_user, target
):
    client.force_login(create_user("plain"))

    response = client.post(revoke_url(target))

    assert response.status_code == 302
    assert response.url == reverse("common:login")
    assert_untouched(target)


@pytest.mark.django_db
def test_inactive_superuser_cannot_revoke_tokens(client, create_user, target):
    client.force_login(create_user("gone", is_superuser=True, is_active=False))

    response = client.post(revoke_url(target))

    assert response.status_code == 302
    assert response.url.startswith(reverse("common:login"))
    assert_untouched(target)


@pytest.mark.django_db
def test_revocation_is_protected_against_csrf(superuser, target):
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(superuser)

    response = browser.post(revoke_url(target))

    assert response.status_code == 403
    assert_untouched(target)


# -- user management shows the state, never the token ------------------------


@pytest.mark.django_db
def test_user_detail_shows_token_state_without_the_token(superuser_client, target):
    response = superuser_client.get(detail_url(target))

    content = response.content.decode()
    assert response.context["has_api_token"] is True
    assert "This user has an API token. The token itself is not shown here." in content
    assert f'action="{revoke_url(target)}"' in content
    assert "The current API token will stop working immediately." in content
    assert target.key not in content

    content = superuser_client.get(reverse("office:settings.users.list")).content
    assert target.key not in content.decode()


@pytest.mark.django_db
def test_user_detail_context_only_holds_the_token_state(superuser_client, target):
    response = superuser_client.get(detail_url(target))

    assert response.context["has_api_token"] is True
    values = {}
    for layer in response.context:
        values.update(layer.flatten())
    assert {"has_api_token", "user", "object", "form", "view"} <= set(values)
    for name, value in values.items():
        assert not isinstance(value, Token), name
        assert target.key not in repr(value), name
        assert target.key not in str(value), name
    # the account object did not load its token either
    for name in ("user", "object"):
        assert values[name] == target
        assert "auth_token" not in values[name]._state.fields_cache


@pytest.mark.django_db
def test_user_detail_without_token_offers_no_revocation(superuser_client, create_user):
    other = create_user("other", is_staff=True)

    response = superuser_client.get(detail_url(other))

    content = response.content.decode()
    assert response.context["has_api_token"] is False
    assert "This user has no API token." in content
    assert "A new one is created when the user opens their API token page." in content
    assert revoke_url(other) not in content
    # looking at the account does not issue a token for it
    assert keys_of(other) == []


@pytest.mark.django_db
def test_own_profile_has_no_token_administration(superuser_client, superuser):
    Token.objects.create(user=superuser)

    content = superuser_client.get(detail_url(superuser)).content.decode()

    assert "revoke-api-token" not in content
    assert "Revoke API token" not in content


# -- self-service: unchanged behaviour, now audited ---------------------------


@pytest.mark.django_db
def test_first_visit_of_the_token_page_issues_a_token(logged_in_client, user):
    assert keys_of(user) == []

    response = logged_in_client.get(reverse(TOKEN_PAGE))

    assert response.status_code == 200
    (key,) = keys_of(user)
    assert response.context["token"] == key
    assert key in response.content.decode()
    assert api_status(key) == 200
    entry = token_entries().get()
    assert entry.action_type == CREATED
    assert entry.content_object == user
    assert entry.user == user

    # later visits show the same token and write nothing
    response = logged_in_client.get(reverse(TOKEN_PAGE))
    assert response.context["token"] == key
    assert actions() == [CREATED]


@pytest.mark.django_db
def test_user_regenerates_own_token(logged_in_client, user, target):
    old = Token.objects.create(user=user).key
    assert api_status(old) == 200

    response = logged_in_client.post(reverse(TOKEN_REGENERATE))

    assert response.status_code == 302
    assert response.url == reverse(TOKEN_PAGE)
    (new,) = keys_of(user)
    assert new != old
    assert api_status(old) == 401
    assert api_status(new) == 200
    assert keys_of(target) == [target.key]
    assert api_status(target.key) == 200
    entry = token_entries().get()
    assert entry.action_type == REGENERATED
    assert entry.content_object == user
    assert entry.user == user
    assert new in logged_in_client.get(reverse(TOKEN_PAGE)).content.decode()


@pytest.mark.django_db
def test_own_token_survives_a_failed_regeneration(logged_in_client, user, monkeypatch):
    old = Token.objects.create(user=user).key

    def failing_create(*args, **kwargs):
        raise RuntimeError("no token for you")

    monkeypatch.setattr(Token.objects, "create", failing_create)

    with pytest.raises(api_tokens.ApiTokenIssueError):
        logged_in_client.post(reverse(TOKEN_REGENERATE))

    assert keys_of(user) == [old]
    assert api_status(old) == 200
    assert not token_entries().exists()


@pytest.mark.django_db(transaction=True)
def test_request_log_of_a_failed_regeneration_never_contains_a_token(
    logged_in_client, user, monkeypatch, production_errors
):
    """The replacement already exists in the transaction when the audit entry
    fails, with an error that quotes the old and the new token."""
    old = Token.objects.create(user=user).key
    create_entry = LogEntry.objects.create
    issued = []

    def failing_create(*args, **kwargs):
        if kwargs["action_type"] == REGENERATED:
            issued.append(Token.objects.get(user=user).key)
            raise IntegrityError(f"Key (key)=({issued[-1]}) replaces {old}")
        return create_entry(*args, **kwargs)

    monkeypatch.setattr(LogEntry.objects, "create", failing_create)
    logged_in_client.raise_request_exception = False

    response = logged_in_client.post(reverse(TOKEN_REGENERATE))

    assert len(issued) == 1 and issued[0] != old
    production_errors(response, api_tokens.ApiTokenIssueError, old, *issued)
    assert keys_of(user) == [old]
    assert api_status(old) == 200
    assert not token_entries().exists()


@pytest.mark.django_db(transaction=True)
def test_request_log_of_a_failed_first_visit_never_contains_the_token(
    logged_in_client, user, monkeypatch, production_errors
):
    create_entry = LogEntry.objects.create
    issued = []

    def failing_create(*args, **kwargs):
        if kwargs["action_type"] == CREATED:
            issued.append(Token.objects.get(user=user).key)
            raise RuntimeError(f"cannot write the audit entry for {issued[-1]}")
        return create_entry(*args, **kwargs)

    monkeypatch.setattr(LogEntry.objects, "create", failing_create)
    logged_in_client.raise_request_exception = False

    response = logged_in_client.get(reverse(TOKEN_PAGE))

    assert len(issued) == 1
    production_errors(response, api_tokens.ApiTokenIssueError, *issued)
    assert keys_of(user) == []
    assert not token_entries().exists()


@pytest.mark.django_db
def test_owner_gets_a_new_token_after_a_revocation(
    logged_in_client, user, superuser, login_user
):
    """A revocation kills the issued token, it does not lock the account out
    of the API: the owner gets a new token on their own page."""
    first = logged_in_client.get(reverse(TOKEN_PAGE)).context["token"]
    assert api_status(first) == 200

    admin_browser = Client()
    login_user(admin_browser, superuser)
    admin_browser.post(revoke_url(user))
    assert api_status(first) == 401
    assert keys_of(user) == []

    second = logged_in_client.get(reverse(TOKEN_PAGE)).context["token"]

    assert second != first
    assert keys_of(user) == [second]
    assert api_status(second) == 200
    assert api_status(first) == 401
    assert actions() == [CREATED, REVOKED, CREATED]
    assert [entry.user for entry in token_entries()] == [user, superuser, user]


# -- the audit log never contains a token -------------------------------------


@pytest.mark.django_db
def test_tokens_never_reach_the_audit_log(
    logged_in_client, user, superuser, login_user, capsys
):
    created = logged_in_client.get(reverse(TOKEN_PAGE)).context["token"]
    logged_in_client.post(reverse(TOKEN_REGENERATE))
    (regenerated,) = keys_of(user)
    admin_browser = Client()
    login_user(admin_browser, superuser)
    response = admin_browser.post(revoke_url(user), follow=True)
    after_revocation = response.content.decode()
    recreated = logged_in_client.get(reverse(TOKEN_PAGE)).context["token"]
    secrets = {created, regenerated, recreated}
    assert len(secrets) == 3
    assert actions() == [CREATED, REGENERATED, REVOKED, CREATED]

    haystacks = [after_revocation]
    for entry in LogEntry.objects.all():
        haystacks.append(json.dumps([entry.data, entry.auth_data, entry.auth_hash]))
        haystacks.append(str(format_log_entry(entry)))
        haystacks.append(str(format_log_source(entry)))
    for entry in token_entries():
        # only the actor, no further details
        assert entry.data == {"source": str(entry.user)}
    log_page = admin_browser.get(reverse("office:settings.log"))
    assert log_page.status_code == 200
    haystacks.append(log_page.content.decode())
    haystacks.append(admin_browser.get(detail_url(user)).content.decode())
    capsys.readouterr()
    call_command("export_logchain")
    haystacks.append(capsys.readouterr().out)

    assert "API token revoked" in haystacks[-3]
    assert "API token regenerated" in haystacks[-3]
    assert "API token created" in haystacks[-3]
    assert REVOKED in haystacks[-1]
    for haystack in haystacks:
        for secret in secrets:
            assert secret not in haystack
