import logging
import threading

import pytest
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from byro.common import api_tokens
from byro.common.models import LogEntry


def token_entries():
    return LogEntry.objects.filter(
        action_type__startswith="byro.common.user.api_token_"
    ).order_by("id")


def actions():
    return list(token_entries().values_list("action_type", flat=True))


def api_status(key):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
    return client.get(reverse("api:members-list")).status_code


@pytest.fixture
def owner(create_user):
    return create_user("owner", is_staff=True)


@pytest.fixture
def admin(create_user):
    return create_user("root", is_superuser=True)


@pytest.fixture
def failing_audit(monkeypatch):
    """Make writing an audit entry fail, before or after it reached the
    database."""

    def patch(entry_was_written):
        create_entry = LogEntry.objects.create

        def failing_create(*args, **kwargs):
            if entry_was_written:
                create_entry(*args, **kwargs)
            raise RuntimeError("audit log is not available")

        monkeypatch.setattr(LogEntry.objects, "create", failing_create)

    return patch


# -- status ------------------------------------------------------------------


@pytest.mark.django_db
def test_has_token(owner):
    assert api_tokens.has_token(owner) is False
    Token.objects.create(user=owner)
    assert api_tokens.has_token(owner) is True


@pytest.mark.django_db
def test_has_token_does_not_load_the_key(owner):
    token = Token.objects.create(user=owner)

    with CaptureQueriesContext(connection) as queries:
        api_tokens.has_token(owner)

    assert len(queries) == 1
    assert token.key not in str(queries.captured_queries)
    assert "key" not in queries[0]["sql"].split("FROM")[0]


# -- creation ----------------------------------------------------------------


@pytest.mark.django_db
def test_first_request_issues_a_token_and_logs_it(owner):
    token = api_tokens.get_or_create_token(owner, actor=owner)

    assert Token.objects.get(user=owner).key == token.key
    assert api_status(token.key) == 200
    entry = token_entries().get()
    assert entry.action_type == "byro.common.user.api_token_created"
    assert entry.content_object == owner
    assert entry.user == owner


@pytest.mark.django_db
def test_existing_token_is_returned_without_lock_write_or_log(owner):
    token = Token.objects.create(user=owner)

    with CaptureQueriesContext(connection) as queries:
        assert api_tokens.get_or_create_token(owner, actor=owner).key == token.key

    assert len(queries) == 1
    sql = queries[0]["sql"].upper()
    assert sql.lstrip().startswith("SELECT")
    assert "FOR UPDATE" not in sql
    assert not token_entries().exists()


@pytest.mark.parametrize("entry_was_written", (False, True))
@pytest.mark.django_db(transaction=True)
def test_no_token_is_issued_if_the_audit_entry_fails(
    owner, failing_audit, entry_was_written
):
    failing_audit(entry_was_written)

    with pytest.raises(RuntimeError):
        api_tokens.get_or_create_token(owner, actor=owner)

    assert not Token.objects.filter(user=owner).exists()
    assert not token_entries().exists()


# -- regeneration ------------------------------------------------------------


@pytest.mark.django_db
def test_regeneration_replaces_the_token_and_logs_it(owner, admin):
    old = Token.objects.create(user=owner).key
    other = Token.objects.create(user=admin).key
    assert api_status(old) == 200

    new = api_tokens.regenerate_token(owner, actor=owner).key

    assert new != old
    assert api_status(old) == 401
    assert api_status(new) == 200
    assert list(Token.objects.filter(user=owner).values_list("key", flat=True)) == [new]
    assert Token.objects.get(user=admin).key == other
    entry = token_entries().get()
    assert entry.action_type == "byro.common.user.api_token_regenerated"
    assert entry.content_object == owner
    assert entry.user == owner


@pytest.mark.django_db
def test_regeneration_without_a_token_is_logged_as_creation(owner):
    token = api_tokens.regenerate_token(owner, actor=owner)

    assert Token.objects.get(user=owner).key == token.key
    assert actions() == ["byro.common.user.api_token_created"]


@pytest.mark.django_db(transaction=True)
def test_old_token_stays_valid_if_the_new_one_cannot_be_created(owner, monkeypatch):
    old = Token.objects.create(user=owner).key

    def failing_create(*args, **kwargs):
        raise RuntimeError("no token for you")

    monkeypatch.setattr(Token.objects, "create", failing_create)

    with pytest.raises(RuntimeError):
        api_tokens.regenerate_token(owner, actor=owner)

    assert Token.objects.get(user=owner).key == old
    assert api_status(old) == 200
    assert not token_entries().exists()


@pytest.mark.parametrize("entry_was_written", (False, True))
@pytest.mark.django_db(transaction=True)
def test_regeneration_is_rolled_back_if_the_audit_entry_fails(
    owner, failing_audit, entry_was_written
):
    old = Token.objects.create(user=owner).key
    failing_audit(entry_was_written)

    with pytest.raises(RuntimeError):
        api_tokens.regenerate_token(owner, actor=owner)

    assert list(Token.objects.values_list("key", flat=True)) == [old]
    assert api_status(old) == 200
    assert not token_entries().exists()


# -- revocation --------------------------------------------------------------


@pytest.mark.django_db
def test_revocation_removes_the_token_and_logs_it(owner, admin):
    old = Token.objects.create(user=owner).key
    other = Token.objects.create(user=admin).key
    assert api_status(old) == 200

    result = api_tokens.revoke_token(owner, actor=admin)

    assert result == api_tokens.RevokeResult(revoked=True, audited=True)
    assert not Token.objects.filter(user=owner).exists()
    assert api_status(old) == 401
    assert Token.objects.get(user=admin).key == other
    entry = token_entries().get()
    assert entry.action_type == "byro.common.user.api_token_revoked"
    assert entry.content_object == owner
    assert entry.user == admin


@pytest.mark.django_db
def test_revocation_without_a_token_changes_and_logs_nothing(owner, admin):
    result = api_tokens.revoke_token(owner, actor=admin)

    assert result == api_tokens.RevokeResult(revoked=False, audited=False)
    assert not token_entries().exists()


@pytest.mark.parametrize("entry_was_written", (False, True))
@pytest.mark.django_db(transaction=True)
def test_token_stays_revoked_if_the_audit_entry_fails(
    owner, admin, failing_audit, caplog, entry_was_written
):
    """Without the surrounding test transaction of a regular test, so that the
    removal is really committed. Removing a credential takes precedence over
    the completeness of the audit log."""
    old = Token.objects.create(user=owner).key
    failing_audit(entry_was_written)

    with caplog.at_level(logging.ERROR, logger="byro.common.api_tokens"):
        result = api_tokens.revoke_token(owner, actor=admin)

    assert result == api_tokens.RevokeResult(revoked=True, audited=False)
    assert not Token.objects.filter(user=owner).exists()
    assert api_status(old) == 401
    assert not token_entries().exists()
    records = [r for r in caplog.records if r.name == "byro.common.api_tokens"]
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR
    assert "audit log entry could not be written" in records[0].getMessage()
    assert records[0].exc_info
    # the application log names the accounts, never the credential
    assert old not in caplog.text


@pytest.mark.django_db
def test_revocation_refuses_to_run_inside_a_transaction_of_the_caller(owner, admin):
    # a rollback of the caller could bring the token back
    old = Token.objects.create(user=owner).key

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            api_tokens.revoke_token(owner, actor=admin)

    assert Token.objects.get(user=owner).key == old
    assert not token_entries().exists()


# -- locking -----------------------------------------------------------------


def statements_on(queries, table):
    return [
        (index, q["sql"])
        for index, q in enumerate(queries.captured_queries)
        if table in q["sql"]
    ]


@pytest.mark.parametrize("operation", ("create", "regenerate", "revoke"))
@pytest.mark.django_db
def test_writers_read_the_account_under_a_row_lock_first(owner, admin, operation):
    if operation != "create":
        Token.objects.create(user=owner)

    with CaptureQueriesContext(connection) as queries:
        if operation == "create":
            api_tokens.get_or_create_token(owner, actor=owner)
        elif operation == "regenerate":
            api_tokens.regenerate_token(owner, actor=owner)
        else:
            api_tokens.revoke_token(owner, actor=admin)

    lock_index, lock = statements_on(queries, "auth_user")[0]
    assert lock.lstrip().upper().startswith("SELECT")
    # SQLite has no row locks, it serializes writers as a whole
    if connection.features.has_select_for_update:
        assert "FOR UPDATE" in lock.upper()
    token_writes = [
        index
        for index, sql in statements_on(queries, "authtoken_token")
        if not sql.lstrip().upper().startswith("SELECT")
    ]
    assert token_writes and min(token_writes) > lock_index


@pytest.mark.parametrize("audit_fails", (False, True))
@pytest.mark.django_db(transaction=True)
def test_removal_is_not_committed_before_the_audit_attempt(
    owner, admin, monkeypatch, audit_fails
):
    """The removal and its audit attempt are one transaction. Two separately
    committed steps would release the row lock in between and let another
    token writer slip in."""
    Token.objects.create(user=owner)
    create_entry = LogEntry.objects.create
    seen = {}

    def create_during_revocation(*args, **kwargs):
        seen["blocks"] = list(connection.atomic_blocks)
        seen["savepoints"] = list(connection.savepoint_ids)
        seen["autocommit"] = transaction.get_autocommit()
        seen["token_exists"] = Token.objects.filter(user=owner).exists()
        if audit_fails:
            raise RuntimeError("audit log is not available")
        return create_entry(*args, **kwargs)

    monkeypatch.setattr(LogEntry.objects, "create", create_during_revocation)

    result = api_tokens.revoke_token(owner, actor=admin)

    assert result == api_tokens.RevokeResult(revoked=True, audited=not audit_fails)
    # the token is already gone, in the still open, durable transaction that
    # holds the row lock; the audit entry only gets a savepoint in it
    assert seen["token_exists"] is False
    assert seen["autocommit"] is False
    assert len(seen["blocks"]) == 2
    assert seen["blocks"][0].durable
    assert len(seen["savepoints"]) == 1
    assert not connection.in_atomic_block
    assert not Token.objects.filter(user=owner).exists()


def run_on_other_connection(function, outcome, finished):
    """Thread target: Django gives every thread its own database connection."""
    try:
        outcome["value"] = function()
    except Exception as exc:  # reported by the test
        outcome["error"] = exc
    finally:
        connection.close()
        finished.set()


@pytest.fixture
def during_audit_of_revocation(monkeypatch):
    """Run ``function`` on a second database connection at the moment the
    revocation writes its audit entry, and wait for it for ``timeout``
    seconds. Returns what was observed."""

    def patch(function, timeout, audit_fails):
        create_entry = LogEntry.objects.create
        observed = {"outcome": {}, "finished": threading.Event()}
        thread = threading.Thread(
            target=run_on_other_connection,
            args=(function, observed["outcome"], observed["finished"]),
        )
        observed["thread"] = thread

        def create_during_revocation(*args, **kwargs):
            if kwargs["action_type"] == api_tokens.LOG_REVOKED:
                thread.start()
                observed["finished_during_audit"] = observed["finished"].wait(timeout)
                if audit_fails:
                    raise RuntimeError("audit log is not available")
            return create_entry(*args, **kwargs)

        monkeypatch.setattr(LogEntry.objects, "create", create_during_revocation)
        return observed

    return patch


needs_row_locks = pytest.mark.skipif(
    not connection.features.has_select_for_update,
    reason="needs a database with row locks and concurrent writers",
)


@needs_row_locks
@pytest.mark.parametrize("audit_fails", (False, True))
@pytest.mark.django_db(transaction=True)
def test_no_token_writer_runs_between_removal_and_audit_attempt(
    owner, admin, during_audit_of_revocation, audit_fails
):
    """A second writer on its own connection has to wait for the row lock
    until the revocation is committed. Its audit entry therefore follows the
    one of the revocation and belongs to a token that was not revoked."""
    old = Token.objects.create(user=owner).key
    observed = during_audit_of_revocation(
        lambda: api_tokens.regenerate_token(owner, actor=owner).key,
        timeout=1,
        audit_fails=audit_fails,
    )

    result = api_tokens.revoke_token(owner, actor=admin)

    observed["thread"].join(timeout=30)
    assert not observed["thread"].is_alive()
    assert "error" not in observed["outcome"]
    # still waiting for the lock while the revocation wrote its audit entry
    assert observed["finished_during_audit"] is False
    assert result == api_tokens.RevokeResult(revoked=True, audited=not audit_fails)

    new = observed["outcome"]["value"]
    assert new != old
    assert list(Token.objects.filter(user=owner).values_list("key", flat=True)) == [new]
    assert api_status(old) == 401
    assert api_status(new) == 200
    # nothing was left to replace, and the creation comes after the revocation
    if audit_fails:
        assert actions() == ["byro.common.user.api_token_created"]
    else:
        assert actions() == [
            "byro.common.user.api_token_revoked",
            "byro.common.user.api_token_created",
        ]


@needs_row_locks
@pytest.mark.django_db(transaction=True)
def test_page_view_during_a_revocation_issues_nothing(
    owner, admin, during_audit_of_revocation
):
    """The removal is not committed yet, so a reader on another connection
    still finds the old token and neither creates nor logs anything."""
    old = Token.objects.create(user=owner).key
    observed = during_audit_of_revocation(
        lambda: api_tokens.get_or_create_token(owner, actor=owner).key,
        timeout=30,
        audit_fails=False,
    )

    api_tokens.revoke_token(owner, actor=admin)

    observed["thread"].join(timeout=30)
    assert observed["finished_during_audit"] is True
    assert observed["outcome"] == {"value": old}
    assert not Token.objects.filter(user=owner).exists()
    assert actions() == ["byro.common.user.api_token_revoked"]
