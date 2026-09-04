import time
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django_otp.oath import TOTP

from byro.mfa import services
from byro.mfa.encryption import SecretDecryptionError, decrypt_secret, encrypt_secret
from byro.mfa.models import (
    RECOVERY_CODE_ALPHABET,
    RECOVERY_CODE_COUNT,
    MFAConfiguration,
    RecoveryCode,
    TOTPDevice,
    validate_account_label,
    validate_no_colon,
)


@pytest.fixture(autouse=True)
def fast_password_hashers(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


def code_for(device, offset=0):
    totp = TOTP(device.bin_key, device.STEP, device.T0, device.DIGITS, device.drift)
    totp.time = time.time() + offset * device.STEP
    return f"{totp.token():06d}"


# -- encryption -------------------------------------------------------------


def test_encrypt_roundtrip():
    secret = b"\x00\x01\x02" + b"x" * 17
    token = encrypt_secret(secret)
    assert token.startswith("v1$")
    assert secret.hex() not in token
    assert decrypt_secret(token) == secret
    # a random nonce makes every encryption unique
    assert encrypt_secret(secret) != token


def test_decrypt_with_wrong_key_fails(settings):
    token = encrypt_secret(b"s" * 20)
    settings.SECRET_KEY = "another-secret-key"
    with pytest.raises(SecretDecryptionError):
        decrypt_secret(token)


def test_decrypt_honours_secret_key_fallbacks(settings):
    old_key = settings.SECRET_KEY
    token = encrypt_secret(b"s" * 20)
    settings.SECRET_KEY = "rotated-secret-key"
    settings.SECRET_KEY_FALLBACKS = [old_key]
    assert decrypt_secret(token) == b"s" * 20
    # new values are encrypted with the new key
    assert decrypt_secret(encrypt_secret(b"t" * 20)) == b"t" * 20


@pytest.mark.parametrize("value", ["", "garbage", "v1$not-base64!", "v0$AAAA", None])
def test_decrypt_rejects_malformed_values(value):
    with pytest.raises(SecretDecryptionError):
        decrypt_secret(value)


# -- TOTP device ------------------------------------------------------------


@pytest.mark.django_db
def test_pending_device_has_encrypted_random_secret(user):
    device = TOTPDevice.create_pending(user)
    other = TOTPDevice.create_pending(user)
    assert not device.confirmed
    assert len(device.bin_key) == 20
    assert device.bin_key != other.bin_key
    assert device.base32_key not in device.encrypted_key
    assert device.bin_key.hex() not in device.encrypted_key
    assert len(device.base32_key) == 32
    assert device.manual_key == " ".join(
        device.base32_key[i : i + 4] for i in range(0, 32, 4)
    )


@pytest.mark.django_db
def test_device_representation_hides_secret(user):
    device = TOTPDevice.create_pending(user)
    for text in (str(device), repr(device)):
        assert device.base32_key not in text
        assert device.encrypted_key not in text


@pytest.mark.django_db
def test_config_url(user, configuration):
    configuration.name = "Test: Verein e.V."
    configuration.save()
    device = TOTPDevice.create_pending(user)
    url = device.config_url
    # issuer is always BYRO, account defaults to "<association> - <username>"
    # (colons in the association name are dropped)
    assert url.startswith(
        "otpauth://totp/BYRO%3ATest%20Verein%20e.V.%20-%20" + user.username + "?"
    )
    assert f"secret={device.base32_key}" in url
    assert "issuer=BYRO" in url
    assert "algorithm=SHA1" in url
    assert "digits=6" in url
    assert "period=30" in url


@pytest.mark.django_db
def test_config_url_uses_configured_account_label(user, configuration):
    user.email = "admin@example.org"
    user.first_name = "Ada"
    user.last_name = "Lovelace"
    user.save()
    config = MFAConfiguration.get_solo()
    config.account_label = "{name} <{email}> @ {association} ({username})"
    config.save()

    device = TOTPDevice.create_pending(user)
    assert config.get_issuer() == "BYRO"
    assert (
        config.render_account_label(user)
        == f"Ada Lovelace <admin@example.org> @ Association Name ({user.username})"
    )
    url = device.config_url
    assert url.startswith(
        "otpauth://totp/BYRO%3AAda%20Lovelace%20%3Cadmin%40example.org%3E"
    )
    assert "issuer=BYRO" in url


@pytest.mark.django_db
def test_account_label_defaults_and_fallbacks(user, configuration):
    config = MFAConfiguration.get_solo()
    assert config.account_label == "{association} - {username}"
    assert config.render_account_label(user) == f"Association Name - {user.username}"

    # an empty field behaves like the default
    config.account_label = ""
    assert config.render_account_label(user) == f"Association Name - {user.username}"

    # no association name yet: no dangling separator
    configuration.name = ""
    configuration.save()
    assert config.render_account_label(user) == user.username

    # only placeholders that render empty: fall back to the username
    config.account_label = "{name}"
    assert config.render_account_label(user) == user.username

    # unknown placeholders are kept literally, never evaluated
    config.account_label = "{username} {__class__} {nope"
    assert config.render_account_label(user) == f"{user.username} {{__class__}} {{nope"


def test_account_label_validators():
    validate_account_label("{username} ({email}) - {name} @ {association}")
    validate_account_label("plain text")
    validate_no_colon("Verein - admin")
    with pytest.raises(ValidationError) as excinfo:
        validate_account_label("{username} {evil}")
    assert "{evil}" in str(excinfo.value)
    with pytest.raises(ValidationError):
        validate_no_colon("BYRO: Verein")


@pytest.mark.django_db
def test_verify_token_accepts_current_and_adjacent_steps(user):
    for offset in (-1, 0, 1):
        device = TOTPDevice.create_pending(user)
        assert device.verify_token(code_for(device, offset)), offset
        assert device.last_used_at is not None
    device = TOTPDevice.create_pending(user)
    assert not device.verify_token(code_for(device, 2))
    assert not device.verify_token(code_for(device, -2))


@pytest.mark.django_db
def test_verify_token_replay_and_garbage(user):
    device = TOTPDevice.create_pending(user)
    code = code_for(device)
    assert device.verify_token(code)
    assert not device.verify_token(code)  # replay
    device.throttle_reset()
    for garbage in ("", "abc", None, "12345678901234567890"):
        assert not device.verify_token(garbage)
        device.throttle_reset()


@pytest.mark.django_db
def test_verify_token_throttles_failures(user):
    device = TOTPDevice.create_pending(user)
    assert not device.verify_token("000000")
    device.refresh_from_db()
    assert device.throttling_failure_count == 1
    allowed, data = device.verify_is_allowed()
    assert not allowed
    assert data["locked_until"] > now()
    # locked: even a correct code fails
    assert not device.verify_token(code_for(device))
    device.throttling_failure_timestamp = now() - timedelta(seconds=10)
    device.save()
    assert device.verify_token(code_for(device))
    assert device.throttling_failure_count == 0


@pytest.mark.django_db
def test_verify_token_with_undecryptable_secret(user, settings):
    device = TOTPDevice.create_pending(user)
    settings.SECRET_KEY = "different-secret"
    assert not device.verify_token("123456")


# -- recovery codes ---------------------------------------------------------


def test_generate_code_format():
    for _ in range(50):
        code = RecoveryCode.generate_code()
        groups = code.split("-")
        assert len(groups) == 3
        assert all(len(g) == 4 for g in groups)
        assert all(c in RECOVERY_CODE_ALPHABET for c in code.replace("-", ""))
        assert not set("01IO") & set(code)


def test_normalize_and_well_formed():
    assert RecoveryCode.normalize(" ab cd-efgh_jklm ") == "ABCDEFGHJKLM"
    assert RecoveryCode.is_well_formed("ABCDEFGHJKLM")
    assert not RecoveryCode.is_well_formed("ABCDEFGHJKL")
    assert not RecoveryCode.is_well_formed("ABCDEFGHJKL0")
    assert not RecoveryCode.is_well_formed("")


@pytest.mark.django_db
def test_regenerate_and_consume(user):
    codes = RecoveryCode.objects.regenerate_for(user)
    assert len(codes) == RECOVERY_CODE_COUNT
    assert len(set(codes)) == RECOVERY_CODE_COUNT
    stored = list(RecoveryCode.objects.filter(user=user))
    assert len(stored) == RECOVERY_CODE_COUNT
    for code in codes:
        assert all(code not in s.code_hash for s in stored)
        assert any(
            check_password(RecoveryCode.normalize(code), s.code_hash) for s in stored
        )

    assert RecoveryCode.objects.consume(user, codes[0])
    assert not RecoveryCode.objects.consume(user, codes[0])
    assert RecoveryCode.objects.remaining_for(user) == RECOVERY_CODE_COUNT - 1
    assert not RecoveryCode.objects.consume(user, "AAAA-AAAA-AAAA")
    assert not RecoveryCode.objects.consume(user, "nonsense")

    other = get_user_model().objects.create(username="other")
    assert not RecoveryCode.objects.consume(other, codes[1])

    new_codes = RecoveryCode.objects.regenerate_for(user)
    assert not set(new_codes) & set(codes)
    assert not RecoveryCode.objects.consume(user, codes[1])
    assert RecoveryCode.objects.consume(user, new_codes[0])


# -- services ---------------------------------------------------------------


@pytest.mark.django_db
def test_backend_user_and_policy(user, configuration):
    assert not services.is_backend_user(AnonymousUser())
    assert services.is_backend_user(user)
    assert not services.mfa_required_for(user)
    assert not services.mfa_required_for(AnonymousUser())

    device = TOTPDevice.create_pending(user)
    assert not services.mfa_required_for(user)  # pending devices do not count
    device.confirmed = True
    device.save()
    assert services.mfa_required_for(user)
    assert services.user_has_mfa(user)

    user.is_active = False
    assert not services.is_backend_user(user)


@pytest.mark.django_db
def test_invalidate_sessions_only_affects_given_user(user):
    other = get_user_model().objects.create(username="other")

    def make_session(u):
        store = SessionStore()
        store["_auth_user_id"] = str(u.pk)
        store.create()
        return store.session_key

    keys = [make_session(user), make_session(user)]
    other_key = make_session(other)
    anonymous = SessionStore()
    anonymous["foo"] = "bar"
    anonymous.create()

    assert services.invalidate_sessions(user) == 2
    assert not Session.objects.filter(session_key__in=keys).exists()
    assert Session.objects.filter(session_key=other_key).exists()
    assert Session.objects.filter(session_key=anonymous.session_key).exists()


@pytest.mark.django_db
def test_disable_mfa_removes_everything_and_logs(user):
    device = TOTPDevice.create_pending(user)
    device.confirmed = True
    device.save()
    RecoveryCode.objects.regenerate_for(user)

    services.disable_mfa(user, source="internal: test")

    assert not TOTPDevice.objects.filter(user=user).exists()
    assert not RecoveryCode.objects.filter(user=user).exists()
    entry = user.logentry_set.filter(action_type=services.LOG_DISABLED).first()
    assert entry is None  # logged against the user as object, not as actor
    from byro.common.models import LogEntry

    entry = LogEntry.objects.get(action_type=services.LOG_DISABLED)
    assert entry.content_object == user
    assert entry.data["source"] == "internal: test"
