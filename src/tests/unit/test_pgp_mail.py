from datetime import timedelta
from email.generator import BytesGenerator
from io import BytesIO

import pytest
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail import EmailMultiAlternatives
from django.core.mail.message import SafeMIMEMultipart
from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone

from byro.common.forms import RegistrationConfigForm
from byro.common.models import LogEntry
from byro.mails.gpgme_backend import GnuPGPGPBackend, PreparedPGPEmail
from byro.mails.models import (
    EMail,
    MemberPGPKey,
    PGPConfiguration,
    PGPKeySource,
    PGPKeyStatus,
    PGPPolicy,
)
from byro.mails.pgp import (
    PGPBackendError,
    SigningKeyInfo,
    get_dashboard_warnings,
    normalize_fingerprint,
)
from byro.mails.registration import PGP_REGISTRATION_FIELD
from byro.mails.send import SendMailException, mail_send_task
from byro.mails.signals import send_pgp_expiry_reminders
from byro.members.forms import CreateMemberForm
from byro.members.models import FeeIntervals, Member

VALID_FINGERPRINT = "0123456789ABCDEF0123456789ABCDEF01234567"
FAKE_BACKEND_PATH = f"{__name__}.FakePGPBackend"
FAILING_BACKEND_PATH = f"{__name__}.FailingPGPBackend"


class FakePGPBackend:
    calls = []

    def import_key(self, fingerprint, keyserver_urls="", timeout=None):
        self.calls.append(("import", tuple(keyserver_urls), timeout))
        return type(
            "ImportResult",
            (),
            {
                "fingerprint": fingerprint,
                "public_key": "public key",
                "status": PGPKeyStatus.UNVERIFIED,
                "expires_at": None,
                "error": "",
            },
        )()

    def encrypt_message(self, email_message, public_key):
        self.calls.append(("encrypt", public_key, email_message.subject))
        email_message.subject = "encrypted:" + email_message.subject
        return email_message

    def sign_message(self, email_message, signing_key_fingerprint):
        self.calls.append(("sign", signing_key_fingerprint, email_message.subject))
        email_message.subject = "signed:" + email_message.subject
        return email_message

    def import_private_key(self, private_key):
        self.calls.append(("import-private", private_key))
        return VALID_FINGERPRINT

    def signing_key_info(self, fingerprint):
        self.calls.append(("signing-key-info", fingerprint))
        return SigningKeyInfo(
            fingerprint=fingerprint,
            user_ids=["PGP Office <pgp-office@example.org>"],
            algorithm="EdDSA 255",
            can_sign=True,
        )

    def fingerprint_from_public_key(self, public_key):
        self.calls.append(("fingerprint", public_key))
        return VALID_FINGERPRINT


class FailingPGPBackend:
    def import_private_key(self, private_key):
        raise PGPBackendError("The uploaded key is not private.")


@pytest.fixture(autouse=True)
def clear_fake_backend_calls():
    FakePGPBackend.calls = []


def test_normalize_fingerprint():
    assert (
        normalize_fingerprint("0123 4567 89ab cdef 0123 4567 89ab cdef 0123 4567")
        == VALID_FINGERPRINT
    )


def test_normalize_fingerprint_rejects_invalid_value():
    with pytest.raises(ValueError):
        normalize_fingerprint("not a fingerprint")


def test_gnupg_backend_normalizes_keyserver_urls():
    backend = GnuPGPGPBackend()

    assert backend._keyserver_urls(
        [
            "keys.openpgp.org",
            "https://keyserver.ubuntu.com",
            "http://pgp.mit.edu",
            "hkps://keys.example.org",
        ]
    ) == [
        "hkps://keys.openpgp.org",
        "hkps://keyserver.ubuntu.com",
        "hkp://pgp.mit.edu",
        "hkps://keys.example.org",
    ]


def test_gnupg_backend_tries_next_keyserver_after_timeout(monkeypatch):
    backend = GnuPGPGPBackend()
    attempted_servers = []

    def run(command, **kwargs):
        if "--recv-keys" in command:
            server = command[command.index("--keyserver") + 1]
            attempted_servers.append(server)
            if len(attempted_servers) == 1:
                raise PGPBackendError("keyserver timed out")
            return type("Result", (), {"stderr": ""})()
        if "--export" in command:
            return type("Result", (), {"stdout": b"public key"})()
        raise AssertionError(f"Unexpected GnuPG command: {command}")

    monkeypatch.setattr(backend, "_run", run)
    monkeypatch.setattr(
        backend,
        "_key_info",
        lambda fingerprint: {
            "revoked": False,
            "expired": False,
            "can_encrypt": True,
            "expires": [],
        },
    )

    result = backend.import_key(
        VALID_FINGERPRINT,
        ["keys-one.example.org", "keys-two.example.org"],
        timeout=5,
    )

    assert attempted_servers == [
        "hkps://keys-one.example.org",
        "hkps://keys-two.example.org",
    ]
    assert result.public_key == "public key"
    assert result.status == PGPKeyStatus.UNVERIFIED
    assert result.error == ""


def test_gnupg_backend_imports_one_signing_private_key(monkeypatch):
    backend = GnuPGPGPBackend()
    import_commands = []
    secret_key_listing = "\n".join(
        [
            ":".join(["sec"] + [""] * 10 + ["s"]),
            ":".join(["fpr"] + [""] * 8 + [VALID_FINGERPRINT]),
        ]
    )

    def run(command, **kwargs):
        if "--list-secret-keys" in command:
            if "--homedir" not in command:
                return type(
                    "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
                )()
            return type(
                "Result",
                (),
                {"returncode": 0, "stdout": secret_key_listing, "stderr": ""},
            )()
        if "--detach-sign" in command:
            return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        if "--import" in command:
            import_commands.append(command)
            return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        raise AssertionError(f"Unexpected GnuPG command: {command}")

    monkeypatch.setattr(backend, "_run", run)
    monkeypatch.setattr(backend, "_ensure_agent", lambda: None)

    assert backend.import_private_key(b"private key") == VALID_FINGERPRINT
    assert len(import_commands) == 2
    assert "--homedir" in import_commands[0]
    assert "--homedir" not in import_commands[1]


def test_gnupg_backend_replaces_existing_private_key(monkeypatch):
    backend = GnuPGPGPBackend()
    commands = []
    secret_key_listing = "\n".join(
        [
            ":".join(["sec"] + [""] * 10 + ["s"]),
            ":".join(["fpr"] + [""] * 8 + [VALID_FINGERPRINT]),
        ]
    )

    def run(command, **kwargs):
        commands.append(command)
        if "--list-secret-keys" in command:
            return type(
                "Result",
                (),
                {"returncode": 0, "stdout": secret_key_listing, "stderr": ""},
            )()
        if "--detach-sign" in command:
            return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        if "--export-secret-keys" in command:
            return type(
                "Result",
                (),
                {"returncode": 0, "stdout": b"old private key", "stderr": b""},
            )()
        if "--delete-secret-keys" in command or "--import" in command:
            return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        raise AssertionError(f"Unexpected GnuPG command: {command}")

    monkeypatch.setattr(backend, "_ensure_agent", lambda: None)
    monkeypatch.setattr(backend, "_run", run)

    assert backend.import_private_key(b"replacement private key") == VALID_FINGERPRINT
    assert any("--delete-secret-keys" in command for command in commands)
    assert any("--export-secret-keys" in command for command in commands)


def test_gnupg_backend_replaces_a_private_key_that_cannot_be_exported(monkeypatch):
    backend = GnuPGPGPBackend()
    commands = []
    secret_key_listing = "\n".join(
        [
            ":".join(["sec"] + [""] * 10 + ["s"]),
            ":".join(["fpr"] + [""] * 8 + [VALID_FINGERPRINT]),
        ]
    )

    def run(command, **kwargs):
        commands.append(command)
        if "--list-secret-keys" in command:
            return type(
                "Result",
                (),
                {"returncode": 0, "stdout": secret_key_listing, "stderr": ""},
            )()
        if "--detach-sign" in command:
            return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        if "--export-secret-keys" in command:
            return type(
                "Result", (), {"returncode": 2, "stdout": b"", "stderr": b"protected"}
            )()
        if "--delete-secret-keys" in command or "--import" in command:
            return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        raise AssertionError(f"Unexpected GnuPG command: {command}")

    monkeypatch.setattr(backend, "_ensure_agent", lambda: None)
    monkeypatch.setattr(backend, "_run", run)

    assert backend.import_private_key(b"replacement private key") == VALID_FINGERPRINT
    assert any("--delete-secret-keys" in command for command in commands)


def test_gnupg_backend_rejects_passphrase_protected_private_key(monkeypatch):
    backend = GnuPGPGPBackend()
    secret_key_listing = "\n".join(
        [
            ":".join(["sec"] + [""] * 10 + ["s"]),
            ":".join(["fpr"] + [""] * 8 + [VALID_FINGERPRINT]),
        ]
    )

    def run(command, **kwargs):
        if "--list-secret-keys" in command:
            return type(
                "Result",
                (),
                {"returncode": 0, "stdout": secret_key_listing, "stderr": ""},
            )()
        if "--detach-sign" in command:
            return type(
                "Result",
                (),
                {"returncode": 2, "stdout": b"", "stderr": b"Bad passphrase"},
            )()
        if "--import" in command:
            return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        raise AssertionError(f"Unexpected GnuPG command: {command}")

    monkeypatch.setattr(backend, "_run", run)

    with pytest.raises(PGPBackendError, match="must not be protected"):
        backend.import_private_key(b"protected private key")


def test_gnupg_backend_rejects_public_key_upload(monkeypatch):
    backend = GnuPGPGPBackend()

    def run(command, **kwargs):
        if "--list-secret-keys" in command:
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        if "--import" in command:
            return type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})()
        raise AssertionError(f"Unexpected GnuPG command: {command}")

    monkeypatch.setattr(backend, "_run", run)

    with pytest.raises(PGPBackendError, match="does not contain a private PGP key"):
        backend.import_private_key(b"public key")


def test_gnupg_backend_reads_signing_key_info(monkeypatch):
    backend = GnuPGPGPBackend()
    agent_started = []
    secret_key_listing = "\n".join(
        [
            ":".join(
                ["sec", "", "255", "22", "", "1700000000", "", "", "", "", "", "sc"]
            ),
            ":".join(
                [
                    "uid",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "PGP Office <pgp-office@example.org>",
                ]
            ),
            ":".join(
                ["ssb", "", "255", "22", "", "", "1800000000", "", "", "", "", "s"]
            ),
        ]
    )

    monkeypatch.setattr(
        backend,
        "_run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 0, "stdout": secret_key_listing, "stderr": ""}
        )(),
    )
    monkeypatch.setattr(backend, "_ensure_agent", lambda: agent_started.append(True))

    info = backend.signing_key_info(VALID_FINGERPRINT)

    assert agent_started == [True]
    assert info.user_ids == ["PGP Office <pgp-office@example.org>"]
    assert info.algorithm == "EdDSA 255"
    assert info.can_sign
    assert info.created_at is not None
    assert info.expires_at is not None


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAKE_BACKEND_PATH)
def test_pgp_configuration_form_imports_private_key(configuration):
    from byro.mails.forms import PGPConfigurationForm

    config = PGPConfiguration.get_solo()
    original_values = {
        field_name: getattr(config, field_name, None)
        for field_name in PGPConfigurationForm(instance=config).fields
    }
    form = PGPConfigurationForm(
        instance=config,
        data={
            field.name: getattr(config, field.name)
            for field in config._meta.fields
            if field.name != "id"
        },
        files={
            "signing_key_file": SimpleUploadedFile(
                "organization-private-key.asc", b"private key"
            )
        },
    )

    assert form.is_valid(), form.errors
    form.import_signing_key()
    form.save()

    config.refresh_from_db()
    assert config.signing_key_fingerprint == VALID_FINGERPRINT
    assert "signing_key_fingerprint" not in form.fields
    assert FakePGPBackend.calls == [("import-private", b"private key")]
    changes = form.get_log_changes(original_values)
    assert "signing_key_file" not in changes
    assert changes["signing_key_fingerprint"] == ("", VALID_FINGERPRINT)


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAILING_BACKEND_PATH)
def test_settings_shows_private_key_upload_errors(configuration, user):
    from byro.mails.forms import PGPConfigurationForm
    from byro.office.views.settings import ConfigurationView

    config = PGPConfiguration.get_solo()
    form = PGPConfigurationForm(
        instance=config,
        data={
            field.name: getattr(config, field.name)
            for field in config._meta.fields
            if field.name != "id"
        },
        files={"signing_key_file": SimpleUploadedFile("public-key.asc", b"public key")},
    )
    assert form.is_valid(), form.errors

    view = ConfigurationView()
    request = RequestFactory().post("/settings")
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    view.setup(request)
    view._original_values = {
        form: {
            field_name: getattr(config, field_name, None) for field_name in form.fields
        }
    }

    response = view.form_valid([form]).render()

    assert response.status_code == 200
    assert b"The uploaded key is not private." in response.content
    assert any(
        "The private PGP signing key could not be imported" in str(message)
        for message in get_messages(request)
    )


@pytest.mark.django_db
def test_pgp_configuration_form_places_private_key_upload_before_fingerprint():
    from byro.mails.forms import PGPConfigurationForm

    form = PGPConfigurationForm()

    assert "signing_key_fingerprint" not in form.fields


@pytest.mark.django_db
def test_pgp_configuration_form_labels_upload_as_replacement_for_existing_key():
    from byro.mails.forms import PGPConfigurationForm

    config = PGPConfiguration.get_solo()
    config.signing_key_fingerprint = VALID_FINGERPRINT

    form = PGPConfigurationForm(instance=config)

    assert str(form.fields["signing_key_file"].label) == "Replace signing key"


def test_prepared_pgp_email_delegates_smtp_required_attributes():
    original = EmailMultiAlternatives(
        "Subject",
        "Body",
        "sender@example.org",
        to=["member@example.org"],
    )
    prepared = PreparedPGPEmail(original, SafeMIMEMultipart("encrypted"))

    assert prepared.encoding == original.encoding
    assert prepared.from_email == "sender@example.org"
    assert prepared.recipients() == ["member@example.org"]
    assert prepared.message().get_content_subtype() == "encrypted"
    assert prepared.message().as_bytes(linesep="\r\n")


def test_gnupg_backend_starts_agent_before_signing(monkeypatch):
    backend = GnuPGPGPBackend()
    agent_started = []

    monkeypatch.setattr(backend, "_ensure_agent", lambda: agent_started.append(True))
    monkeypatch.setattr(backend, "_freeze", lambda email_message: b"mail")
    monkeypatch.setattr(
        backend,
        "_run",
        lambda *args, **kwargs: type(
            "Result", (), {"returncode": 0, "stdout": b"signature", "stderr": b""}
        )(),
    )

    backend.sign_message(
        EmailMultiAlternatives("Subject", "Body", "sender@example.org"),
        VALID_FINGERPRINT,
    )

    assert agent_started == [True]


def test_gnupg_backend_signs_the_exact_mime_part_that_is_attached(monkeypatch):
    backend = GnuPGPGPBackend()
    signed_data = []

    monkeypatch.setattr(backend, "_ensure_agent", lambda: None)

    def run(command, **kwargs):
        signed_data.append(kwargs["input_data"])
        return type(
            "Result", (), {"returncode": 0, "stdout": b"signature", "stderr": b""}
        )()

    monkeypatch.setattr(backend, "_run", run)
    prepared = backend.sign_message(
        EmailMultiAlternatives(
            "Subject", "Body", "sender@example.org", to=["member@example.org"]
        ),
        VALID_FINGERPRINT,
    )

    output = BytesIO()
    BytesGenerator(output, mangle_from_=False).flatten(
        prepared.message().get_payload()[0], linesep="\r\n"
    )

    assert signed_data == [output.getvalue()]


def test_gnupg_backend_explains_how_to_replace_a_passphrase_protected_key(
    monkeypatch,
):
    backend = GnuPGPGPBackend()

    monkeypatch.setattr(backend, "_ensure_agent", lambda: None)
    monkeypatch.setattr(backend, "_freeze", lambda email_message: b"mail")
    monkeypatch.setattr(
        backend,
        "_run",
        lambda *args, **kwargs: type(
            "Result",
            (),
            {
                "returncode": 2,
                "stdout": b"",
                "stderr": b"gpg: Sorry, we are in batchmode - can't get input",
            },
        )(),
    )

    with pytest.raises(PGPBackendError, match="Replace it in the PGP settings"):
        backend.sign_message(
            EmailMultiAlternatives("Subject", "Body", "sender@example.org"),
            VALID_FINGERPRINT,
        )


def test_gnupg_backend_restarts_agent_after_a_failed_launch(monkeypatch):
    backend = GnuPGPGPBackend()
    calls = []
    results = iter(
        [
            type("Result", (), {"returncode": 1, "stdout": b"", "stderr": b"stale"})(),
            type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})(),
            type("Result", (), {"returncode": 0, "stdout": b"", "stderr": b""})(),
        ]
    )

    def run_gpgconf(*arguments):
        calls.append(arguments)
        return next(results)

    monkeypatch.setattr(backend, "_run_gpgconf", run_gpgconf)

    backend._ensure_agent()

    assert calls == [
        ("--launch", "gpg-agent"),
        ("--kill", "gpg-agent"),
        ("--launch", "gpg-agent"),
    ]


@pytest.mark.django_db
def test_registration_config_contains_pgp_fingerprint_field(configuration):
    form = RegistrationConfigForm()

    assert PGP_REGISTRATION_FIELD in form.fields_extra


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND="")
def test_create_member_form_imports_application_fingerprint(configuration):
    configuration.registration_form = [
        {"name": "member__name", "position": 1},
        {"name": "member__email", "position": 2},
        {"name": "membership__start", "position": 3},
        {"name": "membership__interval", "position": 4},
        {"name": "membership__amount", "position": 5},
        {"name": PGP_REGISTRATION_FIELD, "position": 6},
    ]
    configuration.save()

    form = CreateMemberForm(
        data={
            "member__name": "PGP Member",
            "member__direct_address_name": "PGP",
            "member__order_name": "Member",
            "member__email": "pgp@example.org",
            "membership__start": "2026-08-25",
            "membership__interval": FeeIntervals.MONTHLY,
            "membership__amount": "23",
            PGP_REGISTRATION_FIELD: VALID_FINGERPRINT,
        }
    )

    assert form.is_valid(), form.errors
    form.save()

    member = Member.objects.get(email="pgp@example.org")
    key = member.pgp_keys.get()
    assert key.fingerprint == VALID_FINGERPRINT
    assert key.source == PGPKeySource.KEYSERVER
    assert key.status == PGPKeyStatus.PENDING


@pytest.mark.django_db
def test_member_pgp_key_normalizes_fingerprint(member):
    key = MemberPGPKey.objects.create(
        member=member,
        fingerprint="0123 4567 89ab cdef 0123 4567 89ab cdef 0123 4567",
    )

    assert key.fingerprint == VALID_FINGERPRINT
    assert key.status == PGPKeyStatus.PENDING


@pytest.mark.django_db
def test_member_pgp_key_can_be_logged(member):
    key = MemberPGPKey.objects.create(member=member, fingerprint=VALID_FINGERPRINT)

    key.log("test", ".verified", fingerprint=key.fingerprint)

    entry = LogEntry.objects.get(action_type="byro.members.pgp_key.verified")
    assert entry.action_type == "byro.members.pgp_key.verified"
    assert entry.data["fingerprint"] == VALID_FINGERPRINT


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAKE_BACKEND_PATH)
def test_import_member_key_uses_configured_keyservers(member):
    config = PGPConfiguration.get_solo()
    config.keyserver_url = "keys.openpgp.org\nkeyserver.ubuntu.com\npgp.mit.edu"
    config.keyserver_timeout_seconds = 12
    config.save()

    from byro.mails.pgp import import_member_key

    key = import_member_key(member, VALID_FINGERPRINT, PGPKeySource.KEYSERVER)

    assert key.status == PGPKeyStatus.VALID
    assert FakePGPBackend.calls == [
        (
            "import",
            ("keys.openpgp.org", "keyserver.ubuntu.com", "pgp.mit.edu"),
            12,
        )
    ]


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAKE_BACKEND_PATH)
def test_import_member_key_reactivates_existing_key(member):
    key = MemberPGPKey.objects.create(
        member=member,
        fingerprint=VALID_FINGERPRINT,
        public_key="old public key",
        status=PGPKeyStatus.VALID,
        is_active=False,
    )

    from byro.mails.pgp import import_member_key

    imported_key = import_member_key(member, VALID_FINGERPRINT, PGPKeySource.KEYSERVER)

    assert imported_key.pk == key.pk
    assert imported_key.is_active
    assert imported_key.public_key == "public key"


@pytest.mark.django_db
def test_empty_keyserver_setting_uses_default_keyservers():
    config = PGPConfiguration.get_solo()
    config.keyserver_url = ""

    assert config.keyserver_urls == [
        "keys.openpgp.org",
        "keyserver.ubuntu.com",
        "pgp.mit.edu",
    ]


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAKE_BACKEND_PATH)
def test_upload_form_accepts_matching_public_key(member):
    from byro.mails.forms import MemberPGPKeyUploadForm

    form = MemberPGPKeyUploadForm(
        data={"fingerprint": VALID_FINGERPRINT, "public_key": "public key"}
    )

    assert form.is_valid(), form.errors
    key = form.save(commit=False)
    key.member = member
    key.save()

    assert key.status == PGPKeyStatus.VALID
    assert key.source == PGPKeySource.MANUAL_UPLOAD


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAKE_BACKEND_PATH)
def test_upload_form_rejects_mismatching_public_key():
    from byro.mails.forms import MemberPGPKeyUploadForm

    form = MemberPGPKeyUploadForm(
        data={
            "fingerprint": "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
            "public_key": "public key",
        }
    )

    assert not form.is_valid()
    assert "public key does not match" in str(form.errors)


@pytest.mark.django_db
def test_missing_member_key_can_block_mail(member):
    config = PGPConfiguration.get_solo()
    config.encryption_enabled = True
    config.missing_key_policy = PGPPolicy.BLOCK
    config.save()

    from byro.mails.models import EMail

    mail = EMail.objects.create(to=member.email, subject="Test", text="Text")

    with pytest.raises(SendMailException):
        mail.send()

    mail.refresh_from_db()
    assert mail.sent is None


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAKE_BACKEND_PATH)
def test_pgp_block_keeps_successful_recipients_for_retry(member, mailoutbox):
    blocked_member = Member.objects.create(
        email="blocked@example.org", number="2", name="Blocked Member"
    )
    config = PGPConfiguration.get_solo()
    config.encryption_enabled = True
    config.save()
    MemberPGPKey.objects.create(
        member=member,
        fingerprint=VALID_FINGERPRINT,
        public_key="public key",
        status=PGPKeyStatus.VALID,
    )
    blocked_key = MemberPGPKey.objects.create(
        member=blocked_member,
        fingerprint="1111111111111111111111111111111111111111",
        status=PGPKeyStatus.INVALID,
    )
    mail = EMail.objects.create(
        to=f"{member.email},{blocked_member.email}", subject="Test", text="Text"
    )

    with pytest.raises(SendMailException, match="blocked@example.org"):
        mail.send()

    mail.refresh_from_db()
    assert mail.sent is None
    assert mail.delivered_to == [member.email]
    assert list(mail.members.all()) == [member]
    assert len(mailoutbox) == 1

    blocked_key.status = PGPKeyStatus.VALID
    blocked_key.public_key = "blocked member public key"
    blocked_key.save()
    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert set(mail.delivered_to) == {member.email, blocked_member.email}
    assert set(mail.members.all()) == {member, blocked_member}
    assert len(mailoutbox) == 2
    assert [message.to for message in mailoutbox] == [
        [member.email],
        [blocked_member.email],
    ]


@pytest.mark.django_db
def test_mail_send_task_rejects_an_empty_recipient_list():
    with pytest.raises(SendMailException, match="without recipients"):
        mail_send_task(to=[], subject="Test", body="Text", sender="sender@example.org")


@pytest.mark.django_db
def test_missing_member_key_can_fall_back_to_plain_mail(member, mailoutbox):
    config = PGPConfiguration.get_solo()
    config.encryption_enabled = True
    config.missing_key_policy = PGPPolicy.SEND_PLAIN
    config.save()

    from byro.mails.models import EMail

    mail = EMail.objects.create(to=member.email, subject="Test", text="Text")
    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert len(mailoutbox) == 1


@pytest.mark.django_db
def test_missing_key_policy_does_not_block_non_member_mail(mailoutbox):
    config = PGPConfiguration.get_solo()
    config.encryption_enabled = True
    config.missing_key_policy = PGPPolicy.BLOCK
    config.save()

    from byro.mails.models import EMail

    mail = EMail.objects.create(to="office@example.com", subject="Test", text="Text")
    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert len(mailoutbox) == 1


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAKE_BACKEND_PATH)
def test_valid_member_key_is_signed_before_encrypted(member, mailoutbox):
    config = PGPConfiguration.get_solo()
    config.encryption_enabled = True
    config.signing_enabled = True
    config.signing_key_fingerprint = VALID_FINGERPRINT
    config.save()
    MemberPGPKey.objects.create(
        member=member,
        fingerprint=VALID_FINGERPRINT,
        public_key="public key",
        status=PGPKeyStatus.VALID,
    )

    from byro.mails.models import EMail

    mail = EMail.objects.create(to=member.email, subject="Test", text="Text")
    mail.send()

    assert FakePGPBackend.calls == [
        ("sign", VALID_FINGERPRINT, "Test"),
        ("encrypt", "public key", "signed:Test"),
    ]
    assert mailoutbox[0].subject == "encrypted:signed:Test"


@pytest.mark.django_db
@override_settings(BYRO_PGP_BACKEND=FAKE_BACKEND_PATH)
def test_pgp_delivery_treats_to_cc_and_bcc_as_individual_recipients(member, mailoutbox):
    cc_member = Member.objects.create(
        email="cc@example.org", number="2", name="CC Member"
    )
    bcc_member = Member.objects.create(
        email="bcc@example.org", number="3", name="BCC Member"
    )
    config = PGPConfiguration.get_solo()
    config.encryption_enabled = True
    config.save()
    for member_with_key in (member, cc_member, bcc_member):
        MemberPGPKey.objects.create(
            member=member_with_key,
            fingerprint=f"{int(member_with_key.number):040d}",
            public_key=f"public key for {member_with_key.email}",
            status=PGPKeyStatus.VALID,
        )

    mail_send_task(
        to=[member.email],
        cc=[cc_member.email],
        bcc=[bcc_member.email],
        subject="Test",
        body="Text",
        sender="sender@example.org",
    )

    assert {message.to[0] for message in mailoutbox} == {
        member.email,
        cc_member.email,
        bcc_member.email,
    }
    assert all(message.subject == "encrypted:Test" for message in mailoutbox)
    assert all(message.message()["To"] == member.email for message in mailoutbox)
    assert all(message.message()["Cc"] == cc_member.email for message in mailoutbox)
    assert all(message.message()["Bcc"] is None for message in mailoutbox)
    assert {call[1] for call in FakePGPBackend.calls if call[0] == "encrypt"} == {
        f"public key for {member.email}",
        f"public key for {cc_member.email}",
        f"public key for {bcc_member.email}",
    }


@pytest.mark.django_db
def test_dashboard_warns_about_missing_signing_key():
    config = PGPConfiguration.get_solo()
    config.signing_enabled = True
    config.signing_key_fingerprint = ""
    config.save()

    warnings = get_dashboard_warnings()

    assert any(warning["level"] == "danger" for warning in warnings)


@pytest.mark.django_db
def test_dashboard_warns_about_expiring_member_keys(member):
    config = PGPConfiguration.get_solo()
    config.expiry_reminder_days = 30
    config.save()
    MemberPGPKey.objects.create(
        member=member,
        fingerprint=VALID_FINGERPRINT,
        public_key="public key",
        status=PGPKeyStatus.VALID,
        expires_at=timezone.now() + timedelta(days=10),
    )

    warnings = get_dashboard_warnings()

    warning = next(warning for warning in warnings if warning["level"] == "warning")
    assert warning["url"] == reverse("office:members.pgp", kwargs={"pk": member.pk})


@pytest.mark.django_db
def test_dashboard_does_not_warn_about_successful_key_import_output(member):
    MemberPGPKey.objects.create(
        member=member,
        fingerprint=VALID_FINGERPRINT,
        public_key="public key",
        status=PGPKeyStatus.VALID,
        last_error="gpg: public key imported",
    )

    warnings = get_dashboard_warnings()

    assert not any(warning["title"] == "PGP key refresh errors" for warning in warnings)


@pytest.mark.django_db
def test_dashboard_links_one_key_refresh_error_to_its_member_pgp_tab(member):
    MemberPGPKey.objects.create(
        member=member,
        fingerprint=VALID_FINGERPRINT,
        public_key="public key",
        status=PGPKeyStatus.INVALID,
        last_error="keyserver unavailable",
    )

    warnings = get_dashboard_warnings()

    warning = next(
        warning for warning in warnings if warning["title"] == "PGP key refresh errors"
    )
    assert warning["url"] == reverse("office:members.pgp", kwargs={"pk": member.pk})


@pytest.mark.django_db
def test_pgp_expiry_reminder_is_created_as_outbox_draft(member):
    config = PGPConfiguration.get_solo()
    config.expiry_reminder_days = 30
    config.save()
    key = MemberPGPKey.objects.create(
        member=member,
        fingerprint=VALID_FINGERPRINT,
        public_key="public key",
        status=PGPKeyStatus.VALID,
        expires_at=timezone.now() + timedelta(days=10),
    )

    send_pgp_expiry_reminders(sender="test")

    reminder = EMail.objects.get(to=member.email)
    assert reminder.sent is None
    key.refresh_from_db()
    assert key.last_reminder_at is not None
