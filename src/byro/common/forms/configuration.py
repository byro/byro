from django import forms

from byro.common.models import Configuration


class InitialForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    class Meta:
        model = Configuration
        fields = ("name", "backoffice_mail", "mail_from")


class ConfigurationForm(forms.ModelForm):
    class Meta:
        model = Configuration
        fields = (
            "name",
            "address",
            "url",
            "language",
            "currency",
            "mail_from",
            "liability_interval",
        )
