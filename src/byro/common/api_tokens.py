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
with its audit entry. Nothing in here ever logs a token.
"""

import logging
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.authtoken.models import Token

from byro.common.models import LogEntry

logger = logging.getLogger(__name__)

LOG_CREATED = "byro.common.user.api_token_created"
LOG_REGENERATED = "byro.common.user.api_token_regenerated"
LOG_REVOKED = "byro.common.user.api_token_revoked"


@dataclass
class RevokeResult:
    #: A token existed and was removed.
    revoked: bool
    #: The audit entry for the removal was written.
    audited: bool


def has_token(user):
    """Whether ``user`` has an API token. Does not load the token."""
    return Token.objects.filter(user=user).exists()


def _lock(user):
    return get_user_model().objects.select_for_update().get(pk=user.pk)


def get_or_create_token(user, *, actor):
    """Return the token of ``user`` and issue one if there is none yet.

    An existing token is returned without a lock or a write. A new token and
    its audit entry are stored together or not at all.
    """
    token = Token.objects.filter(user=user).first()
    if token is not None:
        return token
    with transaction.atomic():
        locked = _lock(user)
        token, created = Token.objects.get_or_create(user=locked)
        if created:
            LogEntry.objects.create(
                content_object=locked, user=actor, action_type=LOG_CREATED
            )
    return token


def regenerate_token(user, *, actor):
    """Replace the token of ``user`` with a new one and return it.

    The old token, the new token and the audit entry are one transaction: if
    the new token or the audit entry cannot be stored, the old token stays
    valid. If there was no token to replace, the entry records a creation.
    """
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


def revoke_token(user, *, actor):
    """Remove the token of ``user`` without issuing a new one.

    Removing a credential takes precedence over the completeness of the audit
    log: if the audit entry cannot be written, the token stays removed, the
    failure is reported through the application log and in the result.

    The row lock is held from the first read until the commit, so no other
    token writer can run between the removal and its audit attempt. The
    transaction is durable: the removal is committed when this function
    returns, and it refuses to run inside a transaction of the caller, where
    a later rollback could bring the token back.
    """
    audited = False
    with transaction.atomic(durable=True):
        locked = _lock(user)
        deleted, _ = Token.objects.filter(user=locked).delete()
        if deleted:
            try:
                # A savepoint: a failure in here must not undo the removal.
                with transaction.atomic():
                    LogEntry.objects.create(
                        content_object=locked, user=actor, action_type=LOG_REVOKED
                    )
                audited = True
            except Exception:
                logger.exception(
                    "The API token of user %s was revoked by user %s, but the "
                    "audit log entry could not be written.",
                    locked.pk,
                    actor.pk,
                )
    return RevokeResult(revoked=bool(deleted), audited=audited)
