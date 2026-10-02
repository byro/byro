"""Business logic for the API tokens of backend users.

Every change of a token goes through this module, so that it is transactional
and recorded in the audit log:

- ``byro.common.user.api_token_created``: no token existed and one was issued
- ``byro.common.user.api_token_regenerated``: an existing token was
  deliberately replaced
- ``byro.common.user.api_token_revoked``: an existing token was deliberately
  removed

All writers read the account under a row lock first and keep it until their
transaction ends, so per account they run one after the other, each together
with its audit entry.

No token leaves this module except as the return value of the two functions
that issue one. In particular, no exception raised while a token is read,
written or audited leaves it: its message, its representation and its
traceback may contain a token (a unique constraint error quotes the key, for
example), and an uncaught exception ends up in the request log. Such
exceptions are replaced by an :class:`ApiTokenError`, which has a fixed
message and neither cause nor context. For the same reason nothing in here
logs anything that is derived from an exception.
"""

import logging
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.transaction import TransactionManagementError
from rest_framework.authtoken.models import Token

from byro.common.models import LogEntry

logger = logging.getLogger(__name__)

LOG_CREATED = "byro.common.user.api_token_created"
LOG_REGENERATED = "byro.common.user.api_token_regenerated"
LOG_REVOKED = "byro.common.user.api_token_revoked"


class ApiTokenError(RuntimeError):
    """An operation on an API token did not complete.

    Always has the fixed message of its class and never refers to the
    exception that caused it.
    """

    message = "The API token operation could not be completed safely."

    def __init__(self):
        super().__init__(self.message)


class ApiTokenAccountMissing(ApiTokenError):
    message = "The account of the API token does not exist."


class ApiTokenIssueError(ApiTokenError):
    message = "The API token could not be issued safely."


class ApiTokenRevocationError(ApiTokenError):
    """The revocation has no confirmed result. Usually nothing was changed,
    but if the database did not acknowledge a commit, the token may be gone
    nevertheless."""

    message = "The API token revocation could not be completed safely."


@dataclass
class RevokeResult:
    #: A token existed and its removal is committed.
    revoked: bool
    #: The audit entry for the removal is committed, too.
    audited: bool


def has_token(user):
    """Whether ``user`` has an API token. Does not load the token."""
    return Token.objects.filter(user=user).exists()


def _controlled(error, operation, *args):
    """Return ``operation(*args)``. If it fails, raise ``error`` instead of
    its exception.

    The replacement is raised after the ``except`` block has ended, so it has
    no cause and no context, and its traceback holds no frame of
    ``operation``. Nothing is taken from the original exception.
    """
    try:
        return operation(*args)
    except ApiTokenAccountMissing:
        error = ApiTokenAccountMissing
    except Exception:
        pass
    raise error() from None


def _lock(user):
    account = get_user_model().objects.select_for_update().filter(pk=user.pk).first()
    if account is None:
        raise ApiTokenAccountMissing()
    return account


def get_or_create_token(user, *, actor):
    """Return the token of ``user`` and issue one if there is none yet.

    An existing token is returned without a lock or a write. A new token and
    its audit entry are stored together or not at all. Raises
    :class:`ApiTokenIssueError` if that fails.
    """
    return _controlled(ApiTokenIssueError, _get_or_create_token, user, actor)


def _get_or_create_token(user, actor):
    token = Token.objects.filter(user=user).first()
    if token is not None:
        return token
    with transaction.atomic():
        locked = _lock(user)
        # Looks again: another request may have issued the token while this
        # one was waiting for the lock.
        token, created = Token.objects.get_or_create(user=locked)
        if created:
            LogEntry.objects.create(
                content_object=locked, user=actor, action_type=LOG_CREATED
            )
    return token


def regenerate_token(user, *, actor):
    """Replace the token of ``user`` with a new one and return it.

    The old token, the new token and the audit entry are one transaction: if
    the new token or the audit entry cannot be stored, the old token is not
    replaced. If there was no token to replace, the entry records a creation.
    Raises :class:`ApiTokenIssueError` if that fails.
    """
    return _controlled(ApiTokenIssueError, _regenerate_token, user, actor)


def _regenerate_token(user, actor):
    with transaction.atomic():
        locked = _lock(user)
        deleted, _ = Token.objects.filter(user=locked).delete()
        token = Token.objects.create(user=locked)
        LogEntry.objects.create(
            content_object=locked,
            user=actor,
            action_type=LOG_REGENERATED if deleted else LOG_CREATED,
        )
    return token


def _require_autocommit(connection):
    """Refuse to revoke where the removal would not be committed on its own:
    inside a transaction of the caller, or with autocommit switched off. The
    transaction a test case wraps around every test does not count."""
    if any(not block._from_testcase for block in connection.atomic_blocks):
        raise TransactionManagementError(
            "An API token cannot be revoked inside a transaction of the caller."
        )
    if not connection.atomic_blocks and not connection.get_autocommit():
        raise TransactionManagementError(
            "An API token cannot be revoked while autocommit is disabled."
        )


def _write_revocation_entry(connection, target, actor):
    """Write the audit entry inside the transaction that removed the token
    and return whether it is part of that transaction.

    ``False`` means the entry is missing and the transaction is intact, so
    the removal can still be committed: the acting account is gone, writing
    the entry failed and its savepoint was restored, or the savepoint was
    rolled back without an error. If the transaction itself is no longer
    intact, :class:`ApiTokenRevocationError` is raised.
    """
    if actor is None:
        # A foreign key to an account that is gone would only fail when the
        # transaction is committed, and take the removal with it.
        return False
    entry = None
    try:
        with transaction.atomic():
            entry = LogEntry.objects.create(
                content_object=target, user=actor, action_type=LOG_REVOKED
            )
            if transaction.get_rollback():
                # Marked for rollback without an exception. Leaving the block
                # rolls the savepoint back, and the entry with it.
                entry = None
    except Exception:
        entry = None
    # No exception is being handled from here on.
    if connection.needs_rollback or connection.closed_in_transaction:
        # The savepoint could not be restored.
        raise ApiTokenRevocationError()
    if entry is not None and LogEntry.objects.filter(pk=entry.pk).exists():
        return True
    # Fails if the database aborted the whole transaction, and makes sure the
    # removal is still part of it.
    if Token.objects.filter(user=target).exists():
        raise ApiTokenRevocationError()
    return False


def _revoke_token(connection, target_id, actor_id):
    User = get_user_model()
    audited = False
    with transaction.atomic(durable=True):
        # Both accounts in one statement and in the order of their ids, so two
        # revocations can never wait for each other. The acting account is
        # read again because the audit entry refers to it.
        accounts = {
            account.pk: account
            for account in User.objects.select_for_update()
            .filter(pk__in={target_id, actor_id})
            .order_by("pk")
        }
        target = accounts.get(target_id)
        if target is None:
            raise ApiTokenAccountMissing()
        deleted, _ = Token.objects.filter(user=target).delete()
        if deleted:
            audited = _write_revocation_entry(
                connection, target, accounts.get(actor_id)
            )
        if connection.needs_rollback or connection.closed_in_transaction:
            # Leaving the block would roll back silently.
            raise ApiTokenRevocationError()
    return bool(deleted), audited


def _report_audit_failure(target_id, actor_id):
    """Tell the application log that a committed revocation has no audit
    entry. Fixed text and the two account ids, nothing else."""
    try:
        logger.error(
            "Failed to write API token revocation audit entry for target "
            "user %s, actor %s",
            target_id,
            actor_id,
        )
    except Exception:
        # A broken log handler cannot undo the revocation and must not make
        # it look as if it had failed.
        pass


def revoke_token(user, *, actor):
    """Remove the token of ``user`` without issuing a new one.

    A returned result is definite: ``revoked`` says whether there was a token
    and its removal is committed, ``audited`` whether the audit entry is
    committed with it.

    Removing a credential takes precedence over the completeness of the audit
    log. If only the audit entry is missing and the transaction is intact,
    the removal is committed without it (``audited`` is false) and this is
    reported to the application log after the commit.

    Everything else raises :class:`ApiTokenRevocationError` (or
    :class:`ApiTokenAccountMissing`): the database fails, the transaction is
    aborted or cannot be committed. There is no confirmed result then. A
    failed transaction is rolled back, but a commit the database did not
    acknowledge may have happened: the token must not be described as revoked
    or as unchanged, its state has to be read again.

    The lock on ``user`` is held from the first read until the commit, so no
    other token writer can run between the removal and its audit attempt.

    Has to run outside of any transaction of the caller, with autocommit
    enabled; a later rollback could bring the token back otherwise.
    """
    connection = transaction.get_connection()
    _require_autocommit(connection)
    target_id, actor_id = user.pk, actor.pk
    revoked, audited = _controlled(
        ApiTokenRevocationError, _revoke_token, connection, target_id, actor_id
    )
    # Committed. Nothing below can bring the token back.
    if revoked and not audited:
        _report_audit_failure(target_id, actor_id)
    return RevokeResult(revoked=revoked, audited=audited)
