import os
import subprocess
from datetime import datetime, timezone
from email.generator import BytesGenerator
from email.mime.application import MIMEApplication
from io import BytesIO

from django.conf import settings
from django.core.mail.message import SafeMIMEMultipart
from django.utils.translation import gettext_lazy as _

from byro.mails.pgp import (
    KeyImportResult,
    PGPBackendError,
    PGPBackendUnavailable,
    normalize_fingerprint,
)


class PreparedPGPEmail:
    def __init__(self, original, mime_message):
        self.original = original
        self.mime_message = mime_message

    def __getattr__(self, name):
        return getattr(self.original, name)

    def message(self):
        return self.mime_message

    def recipients(self):
        return self.original.recipients()


class GnuPGPGPBackend:
    def _env(self):
        env = os.environ.copy()
        home = getattr(settings, "BYRO_PGP_HOME", "")
        if home:
            os.makedirs(home, mode=0o700, exist_ok=True)
            env["GNUPGHOME"] = home
        return env

    def _ensure_home(self):
        home = getattr(settings, "BYRO_PGP_HOME", "")
        if home:
            os.makedirs(home, mode=0o700, exist_ok=True)
            os.environ["GNUPGHOME"] = home

    def _run(self, command, *, input_data=None, timeout=None, text=False, check=True):
        try:
            return subprocess.run(
                command,
                env=self._env(),
                input=input_data,
                check=check,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=text,
                timeout=timeout,
            )
        except FileNotFoundError as e:
            raise PGPBackendUnavailable(
                _("The gpg executable is not installed.")
            ) from e
        except subprocess.TimeoutExpired as e:
            raise PGPBackendError(str(e)) from e

    def _freeze(self, email_message):
        out = BytesIO()
        BytesGenerator(out, mangle_from_=False).flatten(email_message.message())
        return out.getvalue()

    def _copy_outer_headers(self, original, target):
        message = original.message()
        for header in ("Subject", "From", "To", "Cc", "Date", "Message-ID"):
            value = message.get(header)
            if value:
                target[header] = value
        for key, value in getattr(original, "extra_headers", {}).items():
            if key not in target:
                target[key] = value

    def _fingerprint_from_public_key(self, public_key):
        result = self._run(
            [
                "gpg",
                "--batch",
                "--with-colons",
                "--import-options",
                "show-only",
                "--import",
            ],
            input_data=public_key,
            text=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if parts[0] == "fpr" and len(parts) > 9 and parts[9]:
                return normalize_fingerprint(parts[9])
        raise PGPBackendError(_("No usable key was found in the public key data."))

    def fingerprint_from_public_key(self, public_key):
        return self._fingerprint_from_public_key(public_key)

    def _import_public_key(self, public_key):
        fingerprint = self._fingerprint_from_public_key(public_key)
        result = self._run(
            ["gpg", "--batch", "--import"],
            input_data=public_key,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise PGPBackendError(result.stderr.strip() or result.stdout.strip())
        return fingerprint

    def encrypt_message(self, email_message, public_key):
        recipient = self._import_public_key(public_key)
        plaintext = self._freeze(email_message)

        result = self._run(
            [
                "gpg",
                "--batch",
                "--yes",
                "--armor",
                "--trust-model",
                "always",
                "--recipient",
                recipient,
                "--encrypt",
            ],
            input_data=plaintext,
            check=False,
        )
        if result.returncode != 0:
            raise PGPBackendError(result.stderr.decode("utf-8", errors="replace"))

        encrypted = SafeMIMEMultipart("encrypted", protocol="application/pgp-encrypted")
        self._copy_outer_headers(email_message, encrypted)
        encrypted.attach(MIMEApplication(b"Version: 1\n", "pgp-encrypted"))
        encrypted.attach(
            MIMEApplication(
                result.stdout,
                "octet-stream",
                Name="encrypted.asc",
            )
        )
        return PreparedPGPEmail(email_message, encrypted)

    def sign_message(self, email_message, signing_key_fingerprint):
        signing_key_fingerprint = normalize_fingerprint(signing_key_fingerprint)
        signed_data = self._freeze(email_message)

        result = self._run(
            [
                "gpg",
                "--batch",
                "--yes",
                "--armor",
                "--pinentry-mode",
                "loopback",
                "--local-user",
                signing_key_fingerprint,
                "--detach-sign",
            ],
            input_data=signed_data,
            check=False,
        )
        if result.returncode != 0:
            raise PGPBackendError(result.stderr.decode("utf-8", errors="replace"))

        signed = SafeMIMEMultipart(
            "signed",
            protocol="application/pgp-signature",
            micalg="pgp-sha256",
        )
        self._copy_outer_headers(email_message, signed)
        signed.attach(email_message.message())
        signed.attach(
            MIMEApplication(result.stdout, "pgp-signature", Name="signature.asc")
        )
        return PreparedPGPEmail(email_message, signed)

    def import_key(self, fingerprint, keyserver_url="", timeout=None):
        fingerprint = normalize_fingerprint(fingerprint)
        keyserver_urls = self._keyserver_urls(keyserver_url)
        last_error = ""

        for server in keyserver_urls:
            command = ["gpg", "--batch", "--recv-keys", fingerprint]
            if server:
                command[1:1] = ["--keyserver", server]

            try:
                result = self._run(command, text=True, timeout=timeout, check=True)
                break
            except subprocess.CalledProcessError as e:
                last_error = e.stderr.strip() or e.stdout.strip()
            except PGPBackendUnavailable:
                raise
            except PGPBackendError as e:
                last_error = str(e)
        else:
            return KeyImportResult(
                fingerprint=fingerprint,
                status="not_found",
                error=last_error,
            )

        public_key = self._run(
            ["gpg", "--batch", "--armor", "--export", fingerprint],
            check=True,
        ).stdout.decode("utf-8")
        key_info = self._key_info(fingerprint)

        return KeyImportResult(
            fingerprint=fingerprint,
            public_key=public_key,
            status=self._status_for_key(key_info),
            expires_at=self._expires_at(key_info),
            error=result.stderr.strip(),
        )

    def _keyserver_urls(self, keyserver_url):
        if isinstance(keyserver_url, (list, tuple)):
            values = keyserver_url
        else:
            values = (keyserver_url or "").splitlines()
        urls = [
            self._normalize_keyserver_url(value.strip())
            for value in values
            if value and value.strip()
        ]
        return urls or [""]

    def _normalize_keyserver_url(self, value):
        if value.startswith("https://"):
            return "hkps://" + value[len("https://") :]
        if value.startswith("http://"):
            return "hkp://" + value[len("http://") :]
        if "://" not in value:
            return "hkps://" + value
        return value

    def _key_info(self, fingerprint):
        result = self._run(
            ["gpg", "--batch", "--with-colons", "--list-keys", fingerprint],
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise PGPBackendError(result.stderr.strip() or result.stdout.strip())

        info = {
            "revoked": False,
            "expired": False,
            "can_encrypt": False,
            "expires": [],
        }
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if parts[0] not in ("pub", "sub"):
                continue
            validity = parts[1]
            capabilities = parts[11] if len(parts) > 11 else ""
            expires = parts[6] if len(parts) > 6 else ""
            info["revoked"] = info["revoked"] or validity == "r"
            info["expired"] = info["expired"] or validity == "e"
            info["can_encrypt"] = info["can_encrypt"] or "e" in capabilities.lower()
            if expires:
                info["expires"].append(int(expires))
        return info

    def _status_for_key(self, key_info):
        if key_info["revoked"]:
            return "revoked"
        if key_info["expired"]:
            return "expired"
        if not key_info["can_encrypt"]:
            return "invalid"
        return "unverified"

    def _expires_at(self, key_info):
        expirations = key_info["expires"]
        if not expirations:
            return None
        expires = min(expirations)
        return datetime.fromtimestamp(expires, tz=timezone.utc)


GPGMEPGPBackend = GnuPGPGPBackend
