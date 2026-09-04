import logging
import re
import secrets
import time
from base64 import b32encode
from urllib.parse import quote, urlencode

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_otp.models import Device, ThrottlingMixin, TimestampMixin
from django_otp.oath import TOTP

from byro.common.models.configuration import ByroConfiguration, Configuration
from byro.mfa.encryption import SecretDecryptionError, decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)


#: Service name shown in authenticator apps (first line of an entry).
ISSUER = "BYRO"
#: Placeholders for the account name shown in authenticator apps (second line).
ACCOUNT_LABEL_PLACEHOLDERS = ("username", "email", "name", "association")
DEFAULT_ACCOUNT_LABEL = "{association} - {username}"
_PLACEHOLDER_RE = re.compile(r"\{([^{}]*)\}")


def _validate_placeholders(value, allowed):
    unknown = [
        name for name in _PLACEHOLDER_RE.findall(value or "") if name not in allowed
    ]
    if unknown:
        raise ValidationError(
            _(
                "Unknown placeholder: %(placeholder)s. Available placeholders: %(available)s"
            ),
            params={
                "placeholder": ", ".join("{%s}" % name for name in unknown),
                "available": ", ".join("{%s}" % name for name in allowed),
            },
        )


def validate_account_label(value):
    _validate_placeholders(value, ACCOUNT_LABEL_PLACEHOLDERS)


def validate_no_colon(value):
    if ":" in (value or ""):
        raise ValidationError(
            _(
                "Colons are not allowed here: authenticator apps use them to separate "
                "the name from the account."
            )
        )


def _otpauth_safe(value):
    """Issuer and account name are separated by a colon in the otpauth label."""
    return " ".join(str(value or "").replace(":", "").split())


def _render_placeholders(template, values):
    return _PLACEHOLDER_RE.sub(
        lambda match: values.get(match.group(1), match.group(0)), template or ""
    )


class MFAConfiguration(ByroConfiguration):
    """Global MFA policy. Shows up automatically on the office settings page."""

    LOG_TARGET_BASE = "byro.mfa.settings"

    require_mfa = models.BooleanField(
        default=False,
        verbose_name=_("Require MFA for all administrators"),
        help_text=_(
            "When enabled, all users with access to the byro backend have to set up "
            "multi-factor authentication with an authenticator app (TOTP). Users "
            "without MFA are asked to set it up at their next login."
        ),
    )
    account_label = models.CharField(
        max_length=128,
        blank=True,
        default=DEFAULT_ACCOUNT_LABEL,
        validators=[validate_account_label, validate_no_colon],
        verbose_name=_("Account name in authenticator apps"),
        help_text=_(
            'Shown below "BYRO" in the authenticator app. Available placeholders: '
            "{username}, {email}, {name} (the user's name) and {association}. "
            "Colons are not allowed."
        ),
    )

    form_title = _("Multi-factor authentication")
    settings_template = "mfa/settings_form.html"

    def __str__(self):
        return "MFA settings"

    def get_absolute_url(self):
        return reverse("office:settings.base")

    def get_issuer(self):
        return ISSUER

    def render_account_label(self, user):
        values = {
            "username": user.get_username(),
            "email": user.email or "",
            "name": user.get_full_name().strip(),
            "association": Configuration.get_solo().name or "",
        }
        rendered = _render_placeholders(
            self.account_label or DEFAULT_ACCOUNT_LABEL, values
        )
        # an empty association name would leave a dangling separator behind
        rendered = _otpauth_safe(rendered).strip(" -|/")
        return rendered or _otpauth_safe(user.get_username())


TOTP_KEY_BYTES = 20  # 160 bit, as recommended by RFC 4226/6238


class TOTPDevice(TimestampMixin, ThrottlingMixin, Device):
    """A user's authenticator app (RFC 6238 TOTP, 6 digits, 30 seconds, SHA-1).

    Based on the django-otp ``Device`` framework, but stores the shared secret
    encrypted at rest (see :mod:`byro.mfa.encryption`). Devices are created
    unconfirmed during enrollment and only count once ``confirmed`` is set.
    """

    STEP = 30
    T0 = 0
    DIGITS = 6
    TOLERANCE = 1  # accept the previous and the next 30 second step as well

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa_totp_devices",
    )
    encrypted_key = models.CharField(max_length=255, editable=False)
    drift = models.SmallIntegerField(default=0)
    last_t = models.BigIntegerField(default=-1)

    class Meta(Device.Meta):
        verbose_name = _("TOTP device")

    def __str__(self):
        return f"{self.name} ({self.user_id})"

    __repr__ = __str__

    @classmethod
    def create_pending(cls, user, name="Authenticator app"):
        key = secrets.token_bytes(TOTP_KEY_BYTES)
        return cls.objects.create(
            user=user, name=name, confirmed=False, encrypted_key=encrypt_secret(key)
        )

    @property
    def bin_key(self):
        return decrypt_secret(self.encrypted_key)

    @property
    def base32_key(self):
        return b32encode(self.bin_key).decode("ascii").rstrip("=")

    @property
    def manual_key(self):
        """The secret for manual entry, in groups of four characters."""
        key = self.base32_key
        return " ".join(key[i : i + 4] for i in range(0, len(key), 4))

    @property
    def config_url(self):
        """otpauth:// URI as understood by all common authenticator apps. The
        account label is configurable in the MFA settings."""
        config = MFAConfiguration.get_solo()
        issuer = config.get_issuer()
        label = f"{issuer}:{config.render_account_label(self.user)}"
        params = urlencode(
            {
                "secret": self.base32_key,
                "issuer": issuer,
                "algorithm": "SHA1",
                "digits": self.DIGITS,
                "period": self.STEP,
            },
            quote_via=quote,
        )
        return f"otpauth://totp/{quote(label)}?{params}"

    def get_throttle_factor(self):
        return getattr(settings, "OTP_TOTP_THROTTLE_FACTOR", 1)

    def verify_token(self, token):
        verify_allowed, _data = self.verify_is_allowed()
        if not verify_allowed:
            return False

        try:
            token = int(str(token).strip())
        except (TypeError, ValueError):
            verified = False
        else:
            try:
                key = self.bin_key
            except SecretDecryptionError:
                logger.error(
                    "TOTP secret of device %s (user %s) cannot be decrypted; "
                    "was SECRET_KEY changed without SECRET_KEY_FALLBACKS?",
                    self.pk,
                    self.user_id,
                )
                return False

            totp = TOTP(key, self.STEP, self.T0, self.DIGITS, self.drift)
            totp.time = time.time()
            # min_t makes sure a code is never accepted twice (replay protection)
            verified = totp.verify(token, self.TOLERANCE, self.last_t + 1)
            if verified:
                self.last_t = totp.t()
                self.drift = totp.drift
                self.throttle_reset(commit=False)
                self.set_last_used_timestamp(commit=False)
                self.save()

        if not verified:
            self.throttle_increment(commit=True)

        return verified


RECOVERY_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I
RECOVERY_CODE_GROUPS = 3
RECOVERY_CODE_GROUP_LENGTH = 4
RECOVERY_CODE_LENGTH = RECOVERY_CODE_GROUPS * RECOVERY_CODE_GROUP_LENGTH  # 60 bit
RECOVERY_CODE_COUNT = 10


class RecoveryCodeManager(models.Manager):
    def unused_for(self, user):
        return self.filter(user=user, used_at__isnull=True)

    def remaining_for(self, user):
        return self.unused_for(user).count()

    def regenerate_for(self, user):
        """Replace all recovery codes of ``user``. Returns the new codes in
        plain text – this is the only time they are available."""
        codes = [self.model.generate_code() for _ in range(RECOVERY_CODE_COUNT)]
        with transaction.atomic():
            self.filter(user=user).delete()
            self.bulk_create(
                [
                    self.model(
                        user=user, code_hash=make_password(self.model.normalize(code))
                    )
                    for code in codes
                ]
            )
        return codes

    def consume(self, user, code):
        """Mark ``code`` as used if it is a valid, unused recovery code of
        ``user``. Consumption is an atomic conditional update, so the same code
        can never succeed twice, even for concurrent requests."""
        normalized = self.model.normalize(code)
        if not self.model.is_well_formed(normalized):
            return False
        for candidate in self.unused_for(user).order_by("pk"):
            if check_password(normalized, candidate.code_hash):
                updated = self.filter(pk=candidate.pk, used_at__isnull=True).update(
                    used_at=now()
                )
                return updated == 1
        return False


class RecoveryCode(models.Model):
    """A single-use fallback code. Only a password hash is stored."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mfa_recovery_codes",
    )
    code_hash = models.CharField(max_length=128, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    objects = RecoveryCodeManager()

    class Meta:
        verbose_name = _("Recovery code")

    def __str__(self):
        return f"Recovery code #{self.pk} ({self.user_id})"

    __repr__ = __str__

    @staticmethod
    def generate_code():
        raw = "".join(
            secrets.choice(RECOVERY_CODE_ALPHABET) for _ in range(RECOVERY_CODE_LENGTH)
        )
        return "-".join(
            raw[i : i + RECOVERY_CODE_GROUP_LENGTH]
            for i in range(0, RECOVERY_CODE_LENGTH, RECOVERY_CODE_GROUP_LENGTH)
        )

    @staticmethod
    def normalize(code):
        return re.sub(r"[^A-Z0-9]", "", str(code or "").upper())

    @staticmethod
    def is_well_formed(normalized):
        return len(normalized) == RECOVERY_CODE_LENGTH and all(
            char in RECOVERY_CODE_ALPHABET for char in normalized
        )
