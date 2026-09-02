import re
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from byro.mails.send import SendMailException

FINGERPRINT_RE = re.compile(r"^[0-9A-F]{40,64}$")
KEYSERVER_URL_SCHEMES = frozenset(("hkp", "hkps", "http", "https"))


class PGPBackendError(Exception):
    pass


class PGPBackendUnavailable(PGPBackendError):
    pass


@dataclass
class KeyImportResult:
    fingerprint: str = ""
    public_key: str = ""
    status: str = "not_found"
    expires_at: object = None
    error: str = ""


@dataclass
class SigningKeyInfo:
    fingerprint: str
    user_ids: list[str] = field(default_factory=list)
    created_at: object = None
    expires_at: object = None
    algorithm: str = ""
    can_sign: bool = False


class DisabledPGPBackend:
    def import_key(self, fingerprint, keyserver_url="", timeout=None):
        raise PGPBackendUnavailable(_("No PGP backend is configured."))

    def encrypt_message(self, email_message, public_key):
        raise PGPBackendUnavailable(_("No PGP backend is configured."))

    def sign_message(self, email_message, signing_key_fingerprint):
        raise PGPBackendUnavailable(_("No PGP backend is configured."))

    def import_private_key(self, private_key):
        raise PGPBackendUnavailable(_("No PGP backend is configured."))

    def signing_key_info(self, fingerprint):
        raise PGPBackendUnavailable(_("No PGP backend is configured."))

    def fingerprint_from_public_key(self, public_key):
        raise PGPBackendUnavailable(_("No PGP backend is configured."))


def normalize_fingerprint(value):
    value = "".join((value or "").upper().split())
    value = value.replace("0X", "")
    if not FINGERPRINT_RE.match(value):
        raise ValueError(_("Enter a valid PGP fingerprint."))
    return value


def get_backend():
    backend_path = getattr(settings, "BYRO_PGP_BACKEND", "")
    if not backend_path:
        return DisabledPGPBackend()

    module_path, class_name = backend_path.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)()


def get_member_for_recipient(address):
    from byro.members.models import Member

    return Member.all_objects.filter(email__iexact=(address or "").strip()).first()


def get_active_key(member):
    from byro.mails.models import PGPKeyStatus

    if not member:
        return None
    return (
        member.pgp_keys.filter(is_active=True)
        .exclude(status__in=[PGPKeyStatus.NOT_FOUND])
        .order_by("-verified_at", "-last_checked_at", "fingerprint")
        .first()
    )


def policy_for_key(config, key):
    from byro.mails.models import PGPKeyStatus

    if not key:
        return config.missing_key_policy
    if key.status == PGPKeyStatus.VALID:
        return None
    if key.status == PGPKeyStatus.EXPIRED:
        return config.expired_key_policy
    if key.status == PGPKeyStatus.UNVERIFIED:
        return config.unverified_key_policy
    return config.invalid_key_policy


def should_block(policy):
    from byro.mails.models import PGPPolicy

    return policy == PGPPolicy.BLOCK


def prepare_email_message(email_message, recipient_address=None):
    from byro.mails.models import PGPConfiguration

    config = PGPConfiguration.get_solo()
    if not config.encryption_enabled and not config.signing_enabled:
        return email_message

    backend = get_backend()

    if config.signing_enabled:
        if not config.signing_key_fingerprint:
            raise SendMailException(
                _("PGP signing is enabled, but no signing key is configured.")
            )
        try:
            email_message = backend.sign_message(
                email_message, config.signing_key_fingerprint
            )
        except PGPBackendError as e:
            raise SendMailException(str(e))

    if not config.encryption_enabled:
        return email_message

    member = get_member_for_recipient(recipient_address)
    if not member:
        return email_message

    key = get_active_key(member)
    policy = policy_for_key(config, key)
    if should_block(policy):
        raise SendMailException(
            _("Cannot send email to {recipient}: no usable PGP key.").format(
                recipient=recipient_address
            )
        )
    if key and key.is_usable_for_encryption:
        try:
            email_message = backend.encrypt_message(email_message, key.public_key)
        except PGPBackendError as e:
            raise SendMailException(str(e))

    return email_message


def import_member_key(member, fingerprint, source):
    from byro.mails.models import (
        MemberPGPKey,
        PGPConfiguration,
        PGPKeySource,
        PGPKeyStatus,
    )

    fingerprint = normalize_fingerprint(fingerprint)
    config = PGPConfiguration.get_solo()
    key, _created = MemberPGPKey.objects.get_or_create(
        member=member,
        fingerprint=fingerprint,
        defaults={"source": PGPKeySource.KEYSERVER},
    )
    key.source = PGPKeySource.KEYSERVER
    key.is_active = True
    key.last_checked_at = timezone.now()

    try:
        result = get_backend().import_key(
            fingerprint,
            config.keyserver_urls,
            timeout=config.keyserver_timeout_seconds,
        )
    except PGPBackendUnavailable as e:
        key.status = "pending"
        key.last_error = str(e)
    except PGPBackendError as e:
        key.status = "invalid"
        key.last_error = str(e)
    else:
        if normalize_fingerprint(result.fingerprint) != fingerprint:
            key.status = PGPKeyStatus.INVALID
            key.last_error = _("Imported key does not match the requested fingerprint.")
        else:
            key.public_key = result.public_key
            if result.status == PGPKeyStatus.UNVERIFIED:
                key.status = PGPKeyStatus.VALID
            else:
                key.status = result.status
            key.expires_at = result.expires_at
            key.last_error = result.error

    key.save()
    return key


def get_dashboard_warnings():
    from byro.mails.models import MemberPGPKey, PGPConfiguration, PGPKeyStatus

    config = PGPConfiguration.get_solo()
    warnings = []

    if config.signing_enabled and not config.signing_key_fingerprint:
        warnings.append(
            {
                "level": "danger",
                "title": _("PGP signing incomplete"),
                "lines": [_("Signing is enabled, but no signing key is configured.")],
                "url": reverse("office:settings.base"),
            }
        )

    problematic_keys = MemberPGPKey.objects.filter(
        is_active=True,
        status__in=[PGPKeyStatus.INVALID, PGPKeyStatus.REVOKED, PGPKeyStatus.EXPIRED],
    )
    if problematic_keys.exists():
        warnings.append(
            {
                "level": "danger",
                "title": _("PGP key problems"),
                "lines": [
                    _(
                        "{count} active member keys are invalid, revoked, or expired."
                    ).format(count=problematic_keys.count())
                ],
                "url": _member_pgp_warning_url(problematic_keys),
            }
        )

    expiry_cutoff = timezone.now() + timedelta(days=config.expiry_reminder_days)
    expiring_keys = MemberPGPKey.objects.filter(
        is_active=True,
        status=PGPKeyStatus.VALID,
        expires_at__isnull=False,
        expires_at__lte=expiry_cutoff,
    )
    if expiring_keys.exists():
        warnings.append(
            {
                "level": "warning",
                "title": _("PGP keys expire soon"),
                "lines": [
                    _("{count} active member keys expire soon.").format(
                        count=expiring_keys.count()
                    )
                ],
                "url": _member_pgp_warning_url(expiring_keys),
            }
        )

    refresh_error_keys = MemberPGPKey.objects.filter(last_error__gt="").exclude(
        status=PGPKeyStatus.VALID
    )
    if refresh_error_keys.exists():
        warnings.append(
            {
                "level": "warning",
                "title": _("PGP key refresh errors"),
                "lines": [
                    _(
                        "{count} member keys have keyserver import or refresh errors."
                    ).format(count=refresh_error_keys.count())
                ],
                "url": _member_pgp_warning_url(refresh_error_keys),
            }
        )

    return warnings


def _member_pgp_warning_url(keys):
    members = list(keys.values_list("member_id", flat=True).distinct()[:2])
    if len(members) == 1:
        return reverse("office:members.pgp", kwargs={"pk": members[0]})
    return reverse("office:members.list")
