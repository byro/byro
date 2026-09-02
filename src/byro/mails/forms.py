from django import forms
from django.utils.translation import gettext_lazy as _

from byro.mails.models import MemberPGPKey, PGPConfiguration, PGPKeySource, PGPKeyStatus
from byro.mails.pgp import PGPBackendError, get_backend, normalize_fingerprint


class PGPConfigurationForm(forms.ModelForm):
    LOG_EXCLUDE_FIELDS = frozenset(("signing_key_file",))
    field_order = (
        "encryption_enabled",
        "signing_enabled",
        "signing_key_file",
        "keyserver_url",
        "missing_key_policy",
        "invalid_key_policy",
        "unverified_key_policy",
        "expired_key_policy",
        "refresh_keys_automatically",
        "key_refresh_interval_days",
        "keyserver_timeout_seconds",
        "send_expiry_reminders",
        "expiry_reminder_days",
    )
    signing_key_file = forms.FileField(
        required=False,
        label=_("Upload private signing key"),
        help_text=_(
            "Upload an ASCII-armored private PGP key without a passphrase. It "
            "is imported into the configured PGP keyring and is not stored in byro."
        ),
    )

    class Meta:
        model = PGPConfiguration
        exclude = ("signing_key_fingerprint",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.imported_signing_key_fingerprint = ""
        self.original_signing_key_fingerprint = self.instance.signing_key_fingerprint
        self.signing_key_info = None
        if self.original_signing_key_fingerprint:
            self.fields["signing_key_file"].label = _("Replace signing key")
            try:
                self.signing_key_info = get_backend().signing_key_info(
                    self.original_signing_key_fingerprint
                )
            except (AttributeError, PGPBackendError):
                pass

    def clean_signing_key_file(self):
        signing_key_file = self.cleaned_data.get("signing_key_file")
        if signing_key_file and signing_key_file.size > 1024 * 1024:
            raise forms.ValidationError(
                _("The private PGP key file must not exceed 1 MiB.")
            )
        return signing_key_file

    def import_signing_key(self):
        signing_key_file = self.cleaned_data.get("signing_key_file")
        if not signing_key_file:
            return

        try:
            signing_key_file.seek(0)
            backend = get_backend()
            if not hasattr(backend, "import_private_key"):
                raise forms.ValidationError(
                    _("The configured PGP backend cannot import private keys.")
                )
            fingerprint = backend.import_private_key(signing_key_file.read())
            self.imported_signing_key_fingerprint = normalize_fingerprint(fingerprint)
        except (PGPBackendError, ValueError) as e:
            raise forms.ValidationError(str(e))
        finally:
            signing_key_file.seek(0)

        self.instance.signing_key_fingerprint = self.imported_signing_key_fingerprint

    def get_additional_log_changes(self, original_values):
        changes = {}
        fingerprint = self.instance.signing_key_fingerprint
        if self.original_signing_key_fingerprint != fingerprint:
            changes["signing_key_fingerprint"] = (
                self.original_signing_key_fingerprint,
                fingerprint,
            )
        return changes


class MemberPGPFingerprintForm(forms.Form):
    fingerprint = forms.CharField(label=_("Fingerprint"), max_length=100)

    def clean_fingerprint(self):
        try:
            return normalize_fingerprint(self.cleaned_data["fingerprint"])
        except ValueError as e:
            raise forms.ValidationError(e)


class MemberPGPKeyUploadForm(forms.ModelForm):
    class Meta:
        model = MemberPGPKey
        fields = ("fingerprint", "public_key")

    def clean_fingerprint(self):
        try:
            return normalize_fingerprint(self.cleaned_data["fingerprint"])
        except ValueError as e:
            raise forms.ValidationError(e)

    def clean(self):
        cleaned_data = super().clean()
        fingerprint = cleaned_data.get("fingerprint")
        public_key = cleaned_data.get("public_key")
        if not fingerprint or not public_key:
            return cleaned_data

        try:
            public_key_fingerprint = get_backend().fingerprint_from_public_key(
                public_key
            )
        except PGPBackendError as e:
            raise forms.ValidationError(str(e))

        if public_key_fingerprint != fingerprint:
            raise forms.ValidationError(
                _("The uploaded public key does not match the entered fingerprint.")
            )
        return cleaned_data

    def save(self, *args, **kwargs):
        self.instance.source = PGPKeySource.MANUAL_UPLOAD
        self.instance.status = PGPKeyStatus.VALID
        return super().save(*args, **kwargs)
