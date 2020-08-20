from django import forms
from django.utils.translation import gettext_lazy as _

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
    update_existing_order_names = forms.BooleanField(
        label=_("Update all order names"), initial=False, required=False,
    )
    update_existing_direct_address_names = forms.BooleanField(
        label=_("Update all address names"), initial=False, required=False,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # TODO update names

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
            "accounting_start",
            "default_order_name",
            "default_direct_address_name",
        )
