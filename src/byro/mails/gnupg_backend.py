import os
import subprocess
import tempfile
from datetime import datetime, timezone
from email.generator import BytesGenerator
from email.mime.application import MIMEApplication
from io import BytesIO

from django.conf import settings
from django.core.mail.message import SafeMIMEMultipart
from django.utils.translation import gettext_lazy as _

from byro.mails.pgp import (
    KEYSERVER_URL_SCHEMES,
    KeyImportResult,
    PGPBackendError,
    PGPBackendUnavailable,
    SigningKeyInfo,
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


class GnuPGBackend:
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

    def _ensure_agent(self):
        result = self._run_gpgconf("--launch", "gpg-agent")
        if result.returncode != 0:
            self._run_gpgconf("--kill", "gpg-agent")
            result = self._run_gpgconf("--launch", "gpg-agent")

        if result.returncode != 0:
            raise PGPBackendError(
                result.stderr.decode("utf-8", errors="replace").strip()
                or result.stdout.decode("utf-8", errors="replace").strip()
            )

    def _run_gpgconf(self, *arguments):
        try:
            return subprocess.run(
                ["gpgconf", *arguments],
                env=self._env(),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise PGPBackendUnavailable(
                _("The gpgconf executable is not installed.")
            ) from e

    def _freeze(self, mime_message):
        out = BytesIO()
        BytesGenerator(out, mangle_from_=False).flatten(mime_message, linesep="\r\n")
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

    def import_private_key(self, private_key):
        with tempfile.TemporaryDirectory(prefix="byro-pgp-") as temporary_home:
            result = self._run(
                ["gpg", "--batch", "--homedir", temporary_home, "--import"],
                input_data=private_key,
                check=False,
            )
            if result.returncode != 0:
                raise PGPBackendError(
                    result.stderr.decode("utf-8", errors="replace").strip()
                    or result.stdout.decode("utf-8", errors="replace").strip()
                )

            secret_keys = self._secret_keys_in_home(temporary_home)

            if len(secret_keys) == 1 and secret_keys[0][1]:
                self._require_unprotected_signing_key(temporary_home, secret_keys[0][0])

        if not secret_keys:
            raise PGPBackendError(
                _(
                    "The uploaded file does not contain a private PGP key. "
                    "Upload an exported private key."
                )
            )
        if len(secret_keys) != 1:
            raise PGPBackendError(
                _("The uploaded file must contain exactly one private PGP key.")
            )

        fingerprint, can_sign = secret_keys[0]
        if not can_sign:
            raise PGPBackendError(
                _("The uploaded private PGP key cannot be used for signing.")
            )

        if self._secret_key_exists(fingerprint):
            result = self._replace_existing_private_key(fingerprint, private_key)
        else:
            result = self._run(
                ["gpg", "--batch", "--import"], input_data=private_key, check=False
            )
        if result.returncode != 0:
            raise PGPBackendError(
                result.stderr.decode("utf-8", errors="replace").strip()
                or result.stdout.decode("utf-8", errors="replace").strip()
            )
        return fingerprint

    def _secret_key_exists(self, fingerprint):
        self._ensure_agent()
        result = self._run(
            ["gpg", "--batch", "--with-colons", "--list-secret-keys", fingerprint],
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise PGPBackendError(result.stderr.strip() or result.stdout.strip())
        return any(line.startswith("sec:") for line in result.stdout.splitlines())

    def _replace_existing_private_key(self, fingerprint, private_key):
        backup = self._run(
            ["gpg", "--batch", "--armor", "--export-secret-keys", fingerprint],
            check=False,
        )
        backup_data = backup.stdout if backup.returncode == 0 else None

        deletion = self._run(
            ["gpg", "--batch", "--yes", "--delete-secret-keys", fingerprint],
            check=False,
        )
        if deletion.returncode != 0:
            raise PGPBackendError(
                deletion.stderr.decode("utf-8", errors="replace").strip()
                or deletion.stdout.decode("utf-8", errors="replace").strip()
            )

        result = self._run(
            ["gpg", "--batch", "--import"], input_data=private_key, check=False
        )
        if result.returncode != 0 and backup_data:
            self._run(
                ["gpg", "--batch", "--import"], input_data=backup_data, check=False
            )
        return result

    def _require_unprotected_signing_key(self, home, fingerprint):
        result = self._run(
            [
                "gpg",
                "--batch",
                "--yes",
                "--homedir",
                home,
                "--pinentry-mode",
                "loopback",
                "--passphrase",
                "",
                "--local-user",
                fingerprint,
                "--output",
                os.path.join(home, "signing-validation.sig"),
                "--detach-sign",
            ],
            input_data=b"byro private-key upload validation",
            check=False,
        )
        if result.returncode != 0:
            raise PGPBackendError(
                _(
                    "The uploaded private PGP key must not be protected by a "
                    "passphrase. Upload a key without a passphrase."
                )
            )

    def signing_key_info(self, fingerprint):
        fingerprint = normalize_fingerprint(fingerprint)
        self._ensure_agent()
        result = self._run(
            ["gpg", "--batch", "--with-colons", "--list-secret-keys", fingerprint],
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise PGPBackendError(result.stderr.strip() or result.stdout.strip())

        info = SigningKeyInfo(fingerprint=fingerprint)
        signing_expirations = []
        found_secret_key = False
        for line in result.stdout.splitlines():
            parts = line.split(":")
            record_type = parts[0]
            if record_type in ("sec", "ssb"):
                found_secret_key = found_secret_key or record_type == "sec"
                capabilities = parts[11] if len(parts) > 11 else ""
                can_sign = "s" in capabilities.lower()
                info.can_sign = info.can_sign or can_sign
                if can_sign and len(parts) > 6 and parts[6]:
                    signing_expirations.append(int(parts[6]))
                if record_type == "sec":
                    info.algorithm = self._key_algorithm(parts)
                    if len(parts) > 5 and parts[5]:
                        info.created_at = datetime.fromtimestamp(
                            int(parts[5]), tz=timezone.utc
                        )
            elif record_type == "uid" and len(parts) > 9 and parts[9]:
                info.user_ids.append(parts[9])

        if not found_secret_key:
            raise PGPBackendError(
                _("No private PGP key was found for this fingerprint.")
            )
        if signing_expirations:
            info.expires_at = datetime.fromtimestamp(
                min(signing_expirations), tz=timezone.utc
            )
        return info

    def _key_algorithm(self, parts):
        algorithm_ids = {
            "1": "RSA",
            "17": "DSA",
            "19": "ECDSA",
            "22": "EdDSA",
        }
        algorithm = algorithm_ids.get(parts[3] if len(parts) > 3 else "", _("Unknown"))
        key_length = parts[2] if len(parts) > 2 else ""
        return f"{algorithm} {key_length}".strip()

    def _secret_keys_in_home(self, home):
        result = self._run(
            [
                "gpg",
                "--batch",
                "--homedir",
                home,
                "--with-colons",
                "--list-secret-keys",
            ],
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise PGPBackendError(result.stderr.strip() or result.stdout.strip())

        keys = []
        current_key = None
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if parts[0] == "sec":
                current_key = {
                    "fingerprint": None,
                    "can_sign": "s" in (parts[11] if len(parts) > 11 else "").lower(),
                }
                keys.append(current_key)
            elif parts[0] == "ssb" and current_key:
                current_key["can_sign"] = (
                    current_key["can_sign"]
                    or "s" in (parts[11] if len(parts) > 11 else "").lower()
                )
            elif parts[0] == "fpr" and current_key and not current_key["fingerprint"]:
                current_key["fingerprint"] = normalize_fingerprint(parts[9])

        return [
            (key["fingerprint"], key["can_sign"]) for key in keys if key["fingerprint"]
        ]

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
        plaintext = self._freeze(email_message.message())

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
        self._ensure_agent()
        signed_part = email_message.message()
        signed_data = self._freeze(signed_part)

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
            error = result.stderr.decode("utf-8", errors="replace")
            if "can't get input" in error:
                raise PGPBackendError(
                    _(
                        "The configured private PGP key is protected by a passphrase. "
                        "Replace it in the PGP settings with a key without a passphrase."
                    )
                )
            raise PGPBackendError(error)

        signed = SafeMIMEMultipart(
            "signed",
            protocol="application/pgp-signature",
            micalg="pgp-sha256",
        )
        self._copy_outer_headers(email_message, signed)
        signed.attach(signed_part)
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
                self._run(command, text=True, timeout=timeout, check=True)
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
            error="",
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
        scheme, separator, server = value.partition("://")
        if not separator:
            return "hkps://" + value
        scheme = scheme.lower()
        if scheme not in KEYSERVER_URL_SCHEMES:
            raise PGPBackendError(
                _("Unsupported keyserver URL scheme: %(scheme)s") % {"scheme": scheme}
            )
        if scheme == "https":
            scheme = "hkps"
        elif scheme == "http":
            scheme = "hkp"
        return scheme + "://" + server

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
