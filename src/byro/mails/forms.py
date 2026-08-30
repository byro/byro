from django import forms
from django.utils.translation import gettext_lazy as _

from byro.mails.models import MemberPGPKey, PGPKeySource, PGPKeyStatus
from byro.mails.pgp import PGPBackendError, get_backend, normalize_fingerprint


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
