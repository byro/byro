import logging
import threading
import time
import traceback

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.transaction import TransactionManagementError
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from byro.common import api_tokens
from byro.common.models import LogEntry

User = get_user_model()


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


def assert_controlled(excinfo, error, *secrets):
    """The exception that left the service is exactly error with its fixed
    message. Nothing leads back to the exception that caused it, and neither
    its traceback nor the frames of the service hold one of secrets."""
    exc = excinfo.value
    assert type(exc) is error
    assert exc.args == (error.message,)
    assert str(exc) == error.message
    assert exc.__cause__ is None
    assert exc.__context__ is None
    rendered = "".join(traceback.format_exception(exc))
    assert "During handling of the above exception" not in rendered
    assert "direct cause of the following exception" not in rendered
    service_frames = [
        frame
        for frame, _ in traceback.walk_tb(exc.__traceback__)
        if frame.f_code.co_filename == api_tokens.__file__
    ]
    assert service_frames
    for secret in secrets:
        assert secret not in rendered
        assert secret not in repr(exc)
        for frame in service_frames:
            assert secret not in repr(frame.f_locals)


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
    owner, monkeypatch, entry_was_written
):
    """The token exists in the transaction when the audit entry fails, and
    the error quotes it."""
    create_entry = LogEntry.objects.create
    issued = []

    def failing_create(*args, **kwargs):
        issued.append(Token.objects.get(user=owner).key)
        if entry_was_written:
            create_entry(*args, **kwargs)
        raise RuntimeError(f"audit log is not available for {issued[-1]}")

    monkeypatch.setattr(LogEntry.objects, "create", failing_create)

    with pytest.raises(api_tokens.ApiTokenIssueError) as excinfo:
        api_tokens.get_or_create_token(owner, actor=owner)

    assert len(issued) == 1
    assert_controlled(excinfo, api_tokens.ApiTokenIssueError, *issued)
    assert not Token.objects.filter(user=owner).exists()
    assert not token_entries().exists()


@pytest.mark.django_db(transaction=True)
def test_first_request_for_a_deleted_account_fails(owner):
    User.objects.filter(pk=owner.pk).delete()

    with pytest.raises(api_tokens.ApiTokenAccountMissing) as excinfo:
        api_tokens.get_or_create_token(owner, actor=owner)

    assert_controlled(excinfo, api_tokens.ApiTokenAccountMissing)
    assert not Token.objects.exists()


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
        # what a database says about a violated unique constraint
        raise IntegrityError(f"Key (key)=({old}) already exists.")

    monkeypatch.setattr(Token.objects, "create", failing_create)

    with pytest.raises(api_tokens.ApiTokenIssueError) as excinfo:
        api_tokens.regenerate_token(owner, actor=owner)

    assert_controlled(excinfo, api_tokens.ApiTokenIssueError, old)
    assert Token.objects.get(user=owner).key == old
    assert api_status(old) == 200
    assert not token_entries().exists()


@pytest.mark.parametrize("entry_was_written", (False, True))
@pytest.mark.django_db(transaction=True)
def test_regeneration_is_rolled_back_if_the_audit_entry_fails(
    owner, monkeypatch, entry_was_written
):
    old = Token.objects.create(user=owner).key
    create_entry = LogEntry.objects.create
    issued = []

    def failing_create(*args, **kwargs):
        issued.append(Token.objects.get(user=owner).key)
        if entry_was_written:
            create_entry(*args, **kwargs)
        raise RuntimeError(f"audit log is not available for {issued[-1]}")

    monkeypatch.setattr(LogEntry.objects, "create", failing_create)

    with pytest.raises(api_tokens.ApiTokenIssueError) as excinfo:
        api_tokens.regenerate_token(owner, actor=owner)

    # the replacement existed in the transaction, and nowhere else
    assert len(issued) == 1 and issued[0] != old
    assert_controlled(excinfo, api_tokens.ApiTokenIssueError, old, *issued)
    assert list(Token.objects.values_list("key", flat=True)) == [old]
    assert api_status(old) == 200
    assert not token_entries().exists()


# -- revocation --------------------------------------------------------------


def revoke(owner, actor):
    """Revoke and check that a returned result is definite: ``revoked`` only
    for a removal that is committed. An exception promises nothing about the
    token, the tests look at the database themselves."""
    old = Token.objects.filter(user=owner).values_list("key", flat=True).first()
    result = api_tokens.revoke_token(owner, actor=actor)
    if old:
        assert result.revoked is True
        assert not Token.objects.filter(key=old).exists()
    else:
        assert result.revoked is False
    return result


def module_records(caplog):
    return [r for r in caplog.records if r.name == "byro.common.api_tokens"]


def assert_reported(caplog, owner, actor):
    """One line with fixed text and the two account ids, nothing else."""
    (record,) = module_records(caplog)
    assert record.levelno == logging.ERROR
    assert record.msg == (
        "Failed to write API token revocation audit entry for target "
        "user %s, actor %s"
    )
    assert record.args == (owner.pk, actor.pk)
    assert all(type(arg) is int for arg in record.args)
    assert record.exc_info is None
    assert record.exc_text is None
    assert record.stack_info is None


@pytest.mark.django_db
def test_revocation_removes_the_token_and_logs_it(owner, admin):
    old = Token.objects.create(user=owner).key
    other = Token.objects.create(user=admin).key
    assert api_status(old) == 200

    result = revoke(owner, admin)

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
    result = revoke(owner, admin)

    assert result == api_tokens.RevokeResult(revoked=False, audited=False)
    assert not token_entries().exists()


@pytest.mark.django_db(transaction=True)
def test_revocation_of_a_deleted_account_fails(owner, admin):
    User.objects.filter(pk=owner.pk).delete()

    with pytest.raises(api_tokens.ApiTokenAccountMissing) as excinfo:
        api_tokens.revoke_token(owner, actor=admin)

    assert_controlled(excinfo, api_tokens.ApiTokenAccountMissing)
    assert not token_entries().exists()


# An audit failure that the savepoint isolates does not undo the removal.


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

    with caplog.at_level(logging.DEBUG):
        result = revoke(owner, admin)

    assert result == api_tokens.RevokeResult(revoked=True, audited=False)
    assert api_status(old) == 401
    assert not token_entries().exists()
    assert_reported(caplog, owner, admin)


@pytest.mark.parametrize("in_test_transaction", (False, True))
def test_audit_entry_rolled_back_without_an_error_is_not_reported_as_written(
    request, monkeypatch, caplog, in_test_transaction
):
    """The entry is really inserted, then its savepoint is marked for
    rollback and the code returns normally. Django rolls the savepoint back
    without raising anything."""
    request.getfixturevalue("db" if in_test_transaction else "transactional_db")
    create_user = request.getfixturevalue("create_user")
    owner = create_user("owner", is_staff=True)
    admin = create_user("root", is_superuser=True)
    old = Token.objects.create(user=owner).key
    create_entry = LogEntry.objects.create
    inserted = []

    def create_and_mark_for_rollback(*args, **kwargs):
        entry = create_entry(*args, **kwargs)
        inserted.append(LogEntry.objects.filter(pk=entry.pk).exists())
        transaction.set_rollback(True)
        return entry

    monkeypatch.setattr(LogEntry.objects, "create", create_and_mark_for_rollback)

    with caplog.at_level(logging.DEBUG):
        result = revoke(owner, admin)

    assert inserted == [True]
    assert result == api_tokens.RevokeResult(revoked=True, audited=False)
    assert not Token.objects.filter(user=owner).exists()
    assert api_status(old) == 401
    assert not token_entries().exists()
    assert_reported(caplog, owner, admin)


@pytest.mark.django_db(transaction=True)
def test_audit_entry_that_is_not_stored_is_not_reported_as_written(
    owner, admin, monkeypatch, caplog
):
    """Whatever the reason: ``audited`` is only true for an entry that is in
    the transaction when it is committed."""
    old = Token.objects.create(user=owner).key
    monkeypatch.setattr(
        LogEntry.objects, "create", lambda *args, **kwargs: LogEntry(**kwargs)
    )

    with caplog.at_level(logging.DEBUG):
        result = revoke(owner, admin)

    assert result == api_tokens.RevokeResult(revoked=True, audited=False)
    assert api_status(old) == 401
    assert not token_entries().exists()
    assert_reported(caplog, owner, admin)


@pytest.mark.django_db(transaction=True)
def test_revocation_by_an_account_that_was_deleted_meanwhile(owner, admin, caplog):
    """The caller still holds the account object, its row is gone. Written
    blindly, the audit entry would violate a foreign key that some databases
    only check at commit, which would undo the removal."""
    old = Token.objects.create(user=owner).key
    stale = User.objects.get(pk=admin.pk)
    User.objects.filter(pk=admin.pk).delete()

    with caplog.at_level(logging.DEBUG):
        result = revoke(owner, stale)

    assert result == api_tokens.RevokeResult(revoked=True, audited=False)
    assert api_status(old) == 401
    assert not token_entries().exists()
    assert_reported(caplog, owner, stale)


# A failure of the transaction itself has no result and a controlled error.


def savepoint_cannot_be_restored(monkeypatch, secret):
    def broken_rollback(self, sid):
        raise OperationalError(f"SAVEPOINT does not exist ({secret})")

    monkeypatch.setattr(BaseDatabaseWrapper, "savepoint_rollback", broken_rollback)


def transaction_silently_lost(monkeypatch, secret):
    """The database aborted the whole transaction (as for a deadlock victim)
    and nothing reports it when the savepoint is restored."""

    def lose_transaction(self, sid):
        with self.cursor() as cursor:
            cursor.execute("ROLLBACK")

    monkeypatch.setattr(BaseDatabaseWrapper, "savepoint_rollback", lose_transaction)
    monkeypatch.setattr(BaseDatabaseWrapper, "savepoint_commit", lambda self, sid: None)


def connection_lost(monkeypatch, secret):
    create_entry = LogEntry.objects.create

    def create_after_disconnect(*args, **kwargs):
        connection.close()
        return create_entry(*args, **kwargs)

    monkeypatch.setattr(LogEntry.objects, "create", create_after_disconnect)


@pytest.mark.parametrize(
    "break_transaction",
    (
        savepoint_cannot_be_restored,
        transaction_silently_lost,
        pytest.param(
            connection_lost,
            marks=pytest.mark.skipif(
                connection.vendor == "sqlite",
                reason="the in-memory test database is never disconnected",
            ),
        ),
    ),
)
@pytest.mark.django_db(transaction=True)
def test_revocation_fails_if_the_transaction_cannot_be_committed(
    owner, admin, monkeypatch, caplog, break_transaction
):
    """An audit failure may only be put aside while the transaction that
    removed the token is intact. Otherwise there is no result, and the error
    that leaves the service says nothing about what happened, although every
    exception involved quotes the token."""
    old = Token.objects.create(user=owner).key

    def failing_create(*args, **kwargs):
        raise RuntimeError(f"audit log is not available for {old}")

    with caplog.at_level(logging.DEBUG), monkeypatch.context() as patch:
        patch.setattr(LogEntry.objects, "create", failing_create)
        break_transaction(patch, old)
        with pytest.raises(api_tokens.ApiTokenRevocationError) as excinfo:
            revoke(owner, admin)

    assert_controlled(excinfo, api_tokens.ApiTokenRevocationError, old)
    assert old not in caplog.text
    # these simulated failures commit nothing
    assert Token.objects.get(user=owner).key == old
    assert api_status(old) == 200
    assert not token_entries().exists()
    # no result, so there is no missing audit entry to report
    assert not module_records(caplog)


@pytest.mark.parametrize("audit_fails", (False, True))
@pytest.mark.django_db(transaction=True)
def test_revocation_fails_if_the_commit_fails(
    owner, admin, failing_audit, monkeypatch, caplog, audit_fails
):
    """What only surfaces at commit, a deferred constraint for example, is
    not an audit failure. Here the database refuses the commit, so nothing is
    stored."""
    old = Token.objects.create(user=owner).key
    if audit_fails:
        failing_audit(False)

    def failing_commit(self):
        raise OperationalError(f"could not commit the removal of {old}")

    with caplog.at_level(logging.DEBUG), monkeypatch.context() as patch:
        patch.setattr(BaseDatabaseWrapper, "commit", failing_commit)
        with pytest.raises(api_tokens.ApiTokenRevocationError) as excinfo:
            revoke(owner, admin)

    assert_controlled(excinfo, api_tokens.ApiTokenRevocationError, old)
    assert Token.objects.get(user=owner).key == old
    assert api_status(old) == 200
    assert not token_entries().exists()
    assert not module_records(caplog)


@pytest.mark.django_db(transaction=True)
def test_unacknowledged_commit_has_no_result(owner, admin, monkeypatch, caplog):
    """The database commits, the acknowledgement never arrives. An error does
    therefore not mean that the token is still valid: the service raises its
    controlled error and returns nothing, although the token is gone."""
    old = Token.objects.create(user=owner).key
    real_commit = BaseDatabaseWrapper.commit

    def commit_without_acknowledgement(self):
        real_commit(self)
        raise OperationalError(f"server closed the connection unexpectedly ({old})")

    with caplog.at_level(logging.DEBUG), monkeypatch.context() as patch:
        patch.setattr(BaseDatabaseWrapper, "commit", commit_without_acknowledgement)
        with pytest.raises(api_tokens.ApiTokenRevocationError) as excinfo:
            api_tokens.revoke_token(owner, actor=admin)

    assert_controlled(excinfo, api_tokens.ApiTokenRevocationError, old)
    assert old not in caplog.text
    # no result was returned and nothing was reported ...
    assert not module_records(caplog)
    # ... while the database did store the removal and its audit entry
    assert not Token.objects.filter(user=owner).exists()
    assert api_status(old) == 401
    assert actions() == ["byro.common.user.api_token_revoked"]


# Reporting a missing audit entry: after the commit, with controlled data.


@pytest.mark.django_db(transaction=True)
def test_missing_audit_entry_is_reported_after_the_commit(
    owner, admin, failing_audit, monkeypatch
):
    Token.objects.create(user=owner)
    failing_audit(False)
    seen = {}

    def report(*args):
        seen["args"] = args
        seen["in_transaction"] = connection.in_atomic_block
        seen["token_exists"] = Token.objects.filter(user=owner).exists()

    monkeypatch.setattr(api_tokens, "_report_audit_failure", report)

    revoke(owner, admin)

    assert seen == {
        "args": (owner.pk, admin.pk),
        "in_transaction": False,
        "token_exists": False,
    }


@pytest.mark.django_db(transaction=True)
def test_broken_log_handler_cannot_undo_the_revocation(owner, admin, failing_audit):
    old = Token.objects.create(user=owner).key
    failing_audit(False)

    class BrokenHandler(logging.Handler):
        calls = 0

        def emit(self, record):
            BrokenHandler.calls += 1
            raise RuntimeError("the log cannot be written")

    handler = BrokenHandler()
    logger = logging.getLogger("byro.common.api_tokens")
    logger.addHandler(handler)
    try:
        result = revoke(owner, admin)
    finally:
        logger.removeHandler(handler)

    assert BrokenHandler.calls == 1
    assert result == api_tokens.RevokeResult(revoked=True, audited=False)
    assert not Token.objects.filter(user=owner).exists()
    assert api_status(old) == 401


@pytest.mark.django_db(transaction=True)
def test_application_log_never_contains_exception_text(
    owner, admin, monkeypatch, caplog
):
    """Messages, representations and tracebacks of exceptions are arbitrary
    text. Here they contain the token."""
    token = Token.objects.create(user=owner)
    old = token.key

    class Leaking(Exception):
        def __repr__(self):
            return f"Leaking({old})"

    def failing_create(*args, **kwargs):
        secret = old  # a local variable, as a traceback with locals shows it
        raise Leaking(f"cannot log the removal of {token!r} ({secret})")

    monkeypatch.setattr(LogEntry.objects, "create", failing_create)

    with caplog.at_level(logging.DEBUG):
        result = revoke(owner, admin)

    assert result == api_tokens.RevokeResult(revoked=True, audited=False)
    assert_reported(caplog, owner, admin)
    assert old not in caplog.text
    for record in caplog.records:
        assert old not in str(vars(record))


@pytest.mark.django_db(transaction=True)
def test_nothing_is_asked_of_the_exception_that_made_the_audit_fail(
    owner, admin, monkeypatch, caplog
):
    """Not even the name of its class: a metaclass can make that anything,
    here the token."""
    old = Token.objects.create(user=owner).key
    asked = []

    class Meta(type):
        @property
        def __name__(cls):
            asked.append("__name__")
            return 42

        def __repr__(cls):
            asked.append("__repr__")
            return old

    class Hostile(Exception, metaclass=Meta):
        def __str__(self):
            asked.append("__str__")
            return old

        def __repr__(self):
            asked.append("__repr__")
            return old

    def failing_create(*args, **kwargs):
        raise Hostile()

    monkeypatch.setattr(LogEntry.objects, "create", failing_create)

    with caplog.at_level(logging.DEBUG):
        result = revoke(owner, admin)

    assert asked == []
    assert result == api_tokens.RevokeResult(revoked=True, audited=False)
    assert_reported(caplog, owner, admin)
    assert old not in caplog.text


# The removal has to be committed on its own.


@pytest.mark.parametrize("in_test_transaction", (False, True))
def test_revocation_refuses_to_run_inside_a_transaction_of_the_caller(
    request, in_test_transaction
):
    """A rollback of the caller could bring the token back. Checked with and
    without the transaction a regular test is wrapped in."""
    request.getfixturevalue("db" if in_test_transaction else "transactional_db")
    create_user = request.getfixturevalue("create_user")
    owner = create_user("owner", is_staff=True)
    admin = create_user("root", is_superuser=True)
    old = Token.objects.create(user=owner).key

    with pytest.raises(TransactionManagementError):
        with transaction.atomic():
            with CaptureQueriesContext(connection) as queries:
                api_tokens.revoke_token(owner, actor=admin)

    # refused before anything was read or written
    assert not queries
    assert Token.objects.get(user=owner).key == old
    assert api_status(old) == 200
    assert not token_entries().exists()


@pytest.mark.django_db(transaction=True)
def test_revocation_refuses_to_run_with_autocommit_disabled(owner, admin):
    """A durable block does not notice this state: it would join the open
    transaction and leave the commit to the caller."""
    old = Token.objects.create(user=owner).key
    transaction.set_autocommit(False)
    try:
        with CaptureQueriesContext(connection) as queries:
            with pytest.raises(TransactionManagementError):
                api_tokens.revoke_token(owner, actor=admin)
        # refused before anything was read or written
        assert not queries
    finally:
        transaction.rollback()
        transaction.set_autocommit(True)

    assert Token.objects.get(user=owner).key == old
    assert api_status(old) == 200
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


@pytest.mark.django_db
def test_revocation_locks_both_accounts_in_one_ordered_statement(owner, admin):
    """One statement in the order of the ids, so two revocations can never
    wait for each other."""
    Token.objects.create(user=owner)

    with CaptureQueriesContext(connection) as queries:
        api_tokens.revoke_token(owner, actor=admin)

    ((index, lock),) = statements_on(queries, "auth_user")
    assert lock.lstrip().upper().startswith("SELECT")
    assert "ORDER BY" in lock.upper()
    assert str(owner.pk) in lock and str(admin.pk) in lock


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

    result = revoke(owner, admin)

    assert result == api_tokens.RevokeResult(revoked=True, audited=not audit_fails)
    # the token is already gone, in the still open, durable transaction that
    # holds the row lock; the audit entry only gets a savepoint in it
    assert seen["token_exists"] is False
    assert seen["autocommit"] is False
    assert len(seen["blocks"]) == 2
    assert seen["blocks"][0].durable
    assert len(seen["savepoints"]) == 1
    assert not connection.in_atomic_block


@pytest.mark.django_db
def test_token_issued_while_waiting_for_the_lock_is_kept(owner, monkeypatch):
    """The request saw no token, another request issued one before this one
    got the lock: it has to look again instead of issuing or logging a
    second one."""
    real_lock = api_tokens._lock
    other_request = []

    def lock_after_another_request(user):
        if not other_request:
            other_request.append(None)
            other_request[0] = api_tokens.get_or_create_token(owner, actor=owner).key
        return real_lock(user)

    monkeypatch.setattr(api_tokens, "_lock", lock_after_another_request)

    token = api_tokens.get_or_create_token(owner, actor=owner)

    assert token.key == other_request[0]
    assert list(Token.objects.values_list("key", flat=True)) == [token.key]
    assert actions() == ["byro.common.user.api_token_created"]


# -- concurrency, with a second database connection --------------------------

needs_row_locks = pytest.mark.skipif(
    not connection.features.has_select_for_update,
    reason="needs a database with row locks and concurrent writers",
)

WAIT = 30


class OtherConnection:
    """Runs ``function`` in a thread, which gives it a database connection of
    its own, and tells how far it got with the account row lock."""

    def __init__(self, function, before_lock=None):
        self.function = function
        self.before_lock = before_lock
        self.thread = threading.Thread(target=self.run)
        self.reached_lock = threading.Event()
        self.acquired_lock = threading.Event()
        self.finished = threading.Event()
        self.backend_pid = None
        self.outcome = {}

    def run(self):
        try:
            self.outcome["value"] = self.function()
        except Exception as exc:  # reported by result()
            self.outcome["error"] = exc
        finally:
            connection.close()
            self.finished.set()

    def lock(self, real_lock, user):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                self.backend_pid = cursor.fetchone()[0]
        self.reached_lock.set()
        if self.before_lock:
            self.before_lock()
        locked = real_lock(user)
        self.acquired_lock.set()
        return locked

    def start(self):
        self.thread.start()

    def is_blocked_by_this_connection(self):
        """Called on the connection that holds the row lock. True once the
        other connection is waiting for exactly that lock."""
        if not self.reached_lock.wait(WAIT):
            return False
        if connection.vendor == "postgresql":
            deadline = time.monotonic() + WAIT
            blocked = False
            while not blocked and time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_backend_pid() = ANY(pg_blocking_pids(%s))",
                        [self.backend_pid],
                    )
                    blocked = cursor.fetchone()[0]
                if not blocked:
                    time.sleep(0.01)
        else:
            # No portable way to ask the database who waits for whom: the
            # lock statement was reached and has not returned.
            blocked = not self.acquired_lock.wait(1)
        return blocked and not self.acquired_lock.is_set()

    def result(self):
        self.thread.join(timeout=WAIT)
        assert not self.thread.is_alive()
        if "error" in self.outcome:
            raise self.outcome["error"]
        return self.outcome["value"]


@pytest.fixture
def other_connection(monkeypatch):
    """Create :class:`OtherConnection` objects whose way through the account
    row lock is observed."""
    real_lock = api_tokens._lock
    others = {}

    def lock(user):
        other = others.get(threading.current_thread())
        if other is None:
            return real_lock(user)
        return other.lock(real_lock, user)

    monkeypatch.setattr(api_tokens, "_lock", lock)

    def create(function, before_lock=None):
        other = OtherConnection(function, before_lock)
        others[other.thread] = other
        return other

    return create


@pytest.fixture
def during_audit_of_revocation(monkeypatch):
    """Call ``callback`` at the moment the revocation writes its audit entry,
    inside its transaction."""

    def patch(callback, audit_fails=False):
        create_entry = LogEntry.objects.create

        def create_during_revocation(*args, **kwargs):
            if kwargs["action_type"] == api_tokens.LOG_REVOKED:
                callback()
                if audit_fails:
                    raise RuntimeError("audit log is not available")
            return create_entry(*args, **kwargs)

        monkeypatch.setattr(LogEntry.objects, "create", create_during_revocation)

    return patch


@needs_row_locks
@pytest.mark.parametrize("audit_fails", (False, True))
@pytest.mark.django_db(transaction=True)
def test_no_token_writer_runs_between_removal_and_audit_attempt(
    owner, admin, other_connection, during_audit_of_revocation, audit_fails
):
    """A second writer on its own connection has to wait for the row lock
    until the revocation is committed. Its audit entry therefore follows the
    one of the revocation and belongs to a token that was not revoked."""
    old = Token.objects.create(user=owner).key
    writer = other_connection(
        lambda: api_tokens.regenerate_token(owner, actor=owner).key
    )
    seen = {}

    def second_writer_arrives():
        writer.start()
        seen["blocked"] = writer.is_blocked_by_this_connection()
        seen["finished"] = writer.finished.is_set()

    during_audit_of_revocation(second_writer_arrives, audit_fails)

    result = revoke(owner, admin)

    new = writer.result()
    # it was waiting for the lock of the revocation during the audit attempt
    assert seen == {"blocked": True, "finished": False}
    assert writer.acquired_lock.is_set()
    assert result == api_tokens.RevokeResult(revoked=True, audited=not audit_fails)
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
    owner, admin, other_connection, during_audit_of_revocation
):
    """The removal is not committed yet, so a reader on another connection
    still finds the old token and neither locks, creates nor logs anything."""
    old = Token.objects.create(user=owner).key
    reader = other_connection(
        lambda: api_tokens.get_or_create_token(owner, actor=owner).key
    )
    seen = {}

    def page_is_viewed():
        reader.start()
        seen["finished"] = reader.finished.wait(WAIT)

    during_audit_of_revocation(page_is_viewed)

    revoke(owner, admin)

    assert reader.result() == old
    assert seen == {"finished": True}
    assert not reader.reached_lock.is_set()
    assert not Token.objects.filter(user=owner).exists()
    assert actions() == ["byro.common.user.api_token_revoked"]


@needs_row_locks
@pytest.mark.django_db(transaction=True)
def test_concurrent_first_visits_issue_one_token(owner, other_connection):
    """Two requests see no token at the same time. Both go for the lock, one
    issues the token, the other one finds it."""
    both_saw_no_token = threading.Barrier(2)
    visits = [
        other_connection(
            lambda: api_tokens.get_or_create_token(owner, actor=owner).key,
            before_lock=lambda: both_saw_no_token.wait(timeout=WAIT),
        )
        for _ in range(2)
    ]

    for visit in visits:
        visit.start()
    keys = [visit.result() for visit in visits]

    # both took the creating path
    assert all(visit.acquired_lock.is_set() for visit in visits)
    assert keys[0] == keys[1]
    assert list(Token.objects.values_list("key", flat=True)) == [keys[0]]
    assert actions() == ["byro.common.user.api_token_created"]
    assert api_status(keys[0]) == 200


@needs_row_locks
@pytest.mark.django_db(transaction=True)
def test_late_first_visit_finds_the_token_of_the_earlier_one(owner, other_connection):
    """A sees no token, B takes the lock and issues one, A gets the lock
    afterwards and looks again."""
    b_is_done = threading.Event()
    a = other_connection(
        lambda: api_tokens.get_or_create_token(owner, actor=owner).key,
        before_lock=lambda: b_is_done.wait(WAIT),
    )

    a.start()
    assert a.reached_lock.wait(WAIT)
    assert not Token.objects.exists()
    issued_by_b = api_tokens.get_or_create_token(owner, actor=owner).key
    assert not a.acquired_lock.is_set()
    b_is_done.set()

    assert a.result() == issued_by_b
    assert list(Token.objects.values_list("key", flat=True)) == [issued_by_b]
    assert actions() == ["byro.common.user.api_token_created"]
