"""Business logic for multi-factor authentication.

Views, middleware and management commands are thin wrappers around these
functions. Nothing in here ever logs or returns TOTP secrets; recovery codes
in plain text are only returned to the caller that generated them.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.db import transaction
from django.urls import reverse
from django.utils.timezone import now
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp import login as otp_login

from byro.common.models import LogEntry
from byro.mfa.encryption import SecretDecryptionError
from byro.mfa.models import MFAConfiguration, RecoveryCode, TOTPDevice

logger = logging.getLogger(__name__)

LOG_ENABLED = "byro.mfa.enabled"
LOG_DISABLED = "byro.mfa.disabled"
LOG_RESET = "byro.mfa.reset"
LOG_RECOVERY_CODES_REGENERATED = "byro.mfa.recovery_codes.regenerated"
LOG_RECOVERY_CODE_USED = "byro.mfa.recovery_code.used"

#: Unconfirmed devices older than this are replaced when the setup page is
#: opened again, and removed by the periodic task.
PENDING_DEVICE_MAX_AGE = timedelta(hours=1)


@dataclass
class VerifyResult:
    verified: bool
    locked_until: datetime | None = None
    remaining_codes: int | None = None
    recovery_codes: list | None = None


@dataclass
class MFAStatus:
    enabled: bool
    device: TOTPDevice | None
    pending_device: TOTPDevice | None
    recovery_codes_remaining: int
    required_by_policy: bool


# -- policy / state ---------------------------------------------------------


def get_confirmed_device(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


def user_has_mfa(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def policy_requires_mfa():
    return MFAConfiguration.get_solo().require_mfa


def is_backend_user(user):
    """byro grants office access to every authenticated, active Django user
    (see ``PermissionMiddleware``); there is no separate staff flag for the
    backend. The MFA policy therefore applies to exactly these users."""
    return bool(getattr(user, "is_authenticated", False) and user.is_active)


def mfa_required_for(user):
    """MFA is required if the user enabled it themselves, or if the global
    policy requires it for all backend users."""
    if not is_backend_user(user):
        return False
    return user_has_mfa(user) or policy_requires_mfa()


def is_verified(request):
    """True if the current session has passed the MFA challenge (or just
    completed the enrollment) for the logged in user."""
    device = getattr(request.user, "otp_device", None)
    return isinstance(device, TOTPDevice) and device.confirmed


def needs_verification(request):
    user = request.user
    return user.is_authenticated and mfa_required_for(user) and not is_verified(request)


def get_verification_url(request, next_url=None):
    """Where to send an unverified user: the challenge if they have an
    authenticator, otherwise (policy) the enrollment."""
    if get_confirmed_device(request.user) is not None:
        url = reverse("mfa:challenge")
    else:
        url = reverse("mfa:setup")
    if next_url:
        url += "?" + urlencode({"next": next_url})
    return url


def get_status(user):
    device = get_confirmed_device(user)
    return MFAStatus(
        enabled=device is not None,
        device=device,
        pending_device=get_pending_device(user),
        recovery_codes_remaining=RecoveryCode.objects.remaining_for(user),
        required_by_policy=policy_requires_mfa(),
    )


# -- session handling -------------------------------------------------------


def clear_session_verification(request):
    request.session.pop(DEVICE_ID_SESSION_KEY, None)
    if hasattr(request.user, "otp_device"):
        request.user.otp_device = None


def reset_session_verification(sender, request, user, **kwargs):
    """``user_logged_in`` receiver: a new login never inherits verification."""
    if request is not None and hasattr(request, "session"):
        request.session.pop(DEVICE_ID_SESSION_KEY, None)


def invalidate_sessions(user):
    """Delete all (database backed) sessions of ``user``. Returns the number
    of removed sessions."""
    count = 0
    user_id = str(user.pk)
    for session in Session.objects.iterator():
        if session.get_decoded().get(SESSION_KEY) == user_id:
            session.delete()
            count += 1
    return count


# -- enrollment -------------------------------------------------------------


def get_pending_device(user):
    cutoff = now() - PENDING_DEVICE_MAX_AGE
    return (
        TOTPDevice.objects.filter(user=user, confirmed=False, created_at__gte=cutoff)
        .order_by("-created_at")
        .first()
    )


def begin_enrollment(user):
    """Return the user's pending (unconfirmed) device, creating a fresh one
    if there is none or the existing one is stale. Nothing is active until
    :func:`confirm_enrollment` succeeds."""
    device = get_pending_device(user)
    if device is not None:
        try:
            device.bin_key
        except SecretDecryptionError:
            # e.g. SECRET_KEY rotated while the setup was open: start over
            device = None
    if device is None:
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        device = TOTPDevice.create_pending(user)
    return device


def cleanup_pending_devices():
    cutoff = now() - PENDING_DEVICE_MAX_AGE
    return TOTPDevice.objects.filter(confirmed=False, created_at__lt=cutoff).delete()[0]


def _check_device(device, token):
    verify_allowed, data = device.verify_is_allowed()
    if not verify_allowed:
        return VerifyResult(False, locked_until=(data or {}).get("locked_until"))
    if device.verify_token(token):
        return VerifyResult(True)
    logger.warning(
        "MFA verification failed for user %s (device %s)", device.user_id, device.pk
    )
    return VerifyResult(False)


def confirm_enrollment(request, device, token):
    """Activate ``device`` if ``token`` is a valid code for it. On success the
    session is marked as verified and fresh recovery codes are returned."""
    user = request.user
    with transaction.atomic():
        device = (
            TOTPDevice.objects.select_for_update()
            .filter(pk=device.pk, user=user, confirmed=False)
            .first()
        )
        if device is None:
            return VerifyResult(False)
        result = _check_device(device, token)
        if not result.verified:
            return result
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        TOTPDevice.objects.filter(user=user).exclude(pk=device.pk).delete()
        codes = RecoveryCode.objects.regenerate_for(user)
        LogEntry.objects.create(content_object=user, user=user, action_type=LOG_ENABLED)
    otp_login(request, device)
    return VerifyResult(True, recovery_codes=codes)


# -- verification -----------------------------------------------------------


def _confirmed_device_for_update(user):
    return (
        TOTPDevice.objects.select_for_update().filter(user=user, confirmed=True).first()
    )


def verify_totp(request, token):
    """Verify a TOTP code for the logged in user and mark the session."""
    with transaction.atomic():
        device = _confirmed_device_for_update(request.user)
        if device is None:
            return VerifyResult(False)
        result = _check_device(device, token)
    if result.verified:
        otp_login(request, device)
    return result


def verify_recovery_code(request, code):
    """Verify and consume a recovery code for the logged in user and mark the
    session. Failed attempts are throttled together with the TOTP device."""
    user = request.user
    with transaction.atomic():
        device = _confirmed_device_for_update(user)
        if device is None:
            return VerifyResult(False)
        verify_allowed, data = device.verify_is_allowed()
        if not verify_allowed:
            return VerifyResult(False, locked_until=(data or {}).get("locked_until"))
        if not RecoveryCode.objects.consume(user, code):
            device.throttle_increment(commit=True)
            logger.warning("MFA recovery code rejected for user %s", user.pk)
            return VerifyResult(False)
        device.throttle_reset(commit=True)
        remaining = RecoveryCode.objects.remaining_for(user)
        LogEntry.objects.create(
            content_object=user,
            user=user,
            action_type=LOG_RECOVERY_CODE_USED,
            data={"remaining": remaining},
        )
    otp_login(request, device)
    return VerifyResult(True, remaining_codes=remaining)


def regenerate_recovery_codes(request, token):
    """Replace all recovery codes after re-confirming with a TOTP code."""
    user = request.user
    with transaction.atomic():
        device = _confirmed_device_for_update(user)
        if device is None:
            return VerifyResult(False)
        result = _check_device(device, token)
        if not result.verified:
            return result
        codes = RecoveryCode.objects.regenerate_for(user)
        LogEntry.objects.create(
            content_object=user, user=user, action_type=LOG_RECOVERY_CODES_REGENERATED
        )
    return VerifyResult(True, recovery_codes=codes)


# -- disabling / reset ------------------------------------------------------


def disable_mfa(user, actor=None, source=None, action_type=LOG_DISABLED, **data):
    """Remove all MFA credentials of ``user`` and write an audit entry."""
    with transaction.atomic():
        TOTPDevice.objects.filter(user=user).delete()
        RecoveryCode.objects.filter(user=user).delete()
        if source:
            data["source"] = source
        LogEntry.objects.create(
            content_object=user, user=actor, action_type=action_type, data=data
        )


def disable_mfa_for_request(request, token):
    """Self-service: disable MFA after re-confirming with a TOTP code. The
    caller has to make sure the policy allows this."""
    user = request.user
    with transaction.atomic():
        device = _confirmed_device_for_update(user)
        if device is None:
            return VerifyResult(False)
        result = _check_device(device, token)
        if not result.verified:
            return result
        disable_mfa(user, actor=user)
    clear_session_verification(request)
    return VerifyResult(True)


def reset_mfa(user, source):
    """Break-glass reset (management command): remove credentials, terminate
    the user's sessions, log it. Does not touch the global policy – if MFA is
    required, the user has to enroll again at the next login."""
    sessions = invalidate_sessions(user)
    disable_mfa(
        user, source=source, action_type=LOG_RESET, sessions_invalidated=sessions
    )
    return sessions
