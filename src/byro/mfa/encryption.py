"""Encryption at rest for TOTP secrets.

TOTP secrets have to be available in plain text for verification, so they
cannot be hashed like passwords. They are stored encrypted with PyNaCl's
``SecretBox`` (XSalsa20-Poly1305) instead. The symmetric key is derived from
Django's ``SECRET_KEY``; ``SECRET_KEY_FALLBACKS`` are honoured for decryption,
so the usual Django key rotation procedure keeps existing devices working.
"""

import base64
import hashlib

import nacl.exceptions
import nacl.secret
from django.conf import settings

PREFIX = "v1$"
_PERSONALIZATION = b"byro-mfa-key-v1"


class SecretDecryptionError(Exception):
    """The stored secret could not be decrypted (wrong or rotated SECRET_KEY,
    corrupted data). The message never contains key material."""


def _derive_key(secret_key):
    return hashlib.blake2b(
        secret_key.encode("utf-8"),
        digest_size=nacl.secret.SecretBox.KEY_SIZE,
        person=_PERSONALIZATION,
    ).digest()


def _boxes():
    yield nacl.secret.SecretBox(_derive_key(settings.SECRET_KEY))
    for fallback in getattr(settings, "SECRET_KEY_FALLBACKS", None) or []:
        yield nacl.secret.SecretBox(_derive_key(fallback))


def encrypt_secret(plaintext):
    """Encrypt ``plaintext`` (bytes) and return an ASCII string for storage."""
    box = next(_boxes())
    encrypted = box.encrypt(plaintext)  # random nonce, prepended to the ciphertext
    return PREFIX + base64.b64encode(bytes(encrypted)).decode("ascii")


def decrypt_secret(token):
    """Decrypt a value produced by :func:`encrypt_secret`."""
    if not isinstance(token, str) or not token.startswith(PREFIX):
        raise SecretDecryptionError("Unknown secret format")
    try:
        raw = base64.b64decode(token[len(PREFIX) :], validate=True)
    except (ValueError, TypeError) as exc:
        raise SecretDecryptionError("Malformed secret") from exc
    for box in _boxes():
        try:
            return box.decrypt(raw)
        except nacl.exceptions.CryptoError:
            continue
    raise SecretDecryptionError(
        "Secret could not be decrypted with the configured keys"
    )
