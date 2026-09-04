from django import forms
from django.utils.translation import gettext_lazy as _

from byro.mfa.models import RecoveryCode, TOTPDevice


class TOTPTokenForm(forms.Form):
    token = forms.CharField(
        label=_("Authentication code"),
        max_length=16,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "autofocus": "autofocus",
                "placeholder": "123456",
            }
        ),
    )

    def clean_token(self):
        value = "".join(self.cleaned_data["token"].split())
        if not (value.isdigit() and len(value) == TOTPDevice.DIGITS):
            raise forms.ValidationError(
                _("Please enter the six-digit code from your authenticator app.")
            )
        return value


class RecoveryCodeForm(forms.Form):
    code = forms.CharField(
        label=_("Recovery code"),
        max_length=32,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "autofocus": "autofocus",
                "placeholder": "XXXX-XXXX-XXXX",
            }
        ),
    )

    def clean_code(self):
        normalized = RecoveryCode.normalize(self.cleaned_data["code"])
        if not RecoveryCode.is_well_formed(normalized):
            raise forms.ValidationError(_("Please enter a valid recovery code."))
        return normalized
