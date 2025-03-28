from django import forms
from django.utils.translation import gettext_lazy as _

from byro.common.models import Configuration
from byro.members.models import Member


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
        label=_("Update all order names"),
        initial=False,
        required=False,
    )
    update_existing_direct_address_names = forms.BooleanField(
        label=_("Update all address names"),
        initial=False,
        required=False,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.cleaned_data.get("update_existing_order_names"):
            for member in Member.objects.all():
                member.update_order_name(force=True)
        if self.cleaned_data.get("update_existing_direct_address_names"):
            for member in Member.objects.all():
                member.update_direct_address_name(force=True)

    class Meta:
        model = Configuration
        fields = (
            "name",
            "address",
            "url",
            "language",
            "currency",
            "currency_symbol",
            "currency_postfix",
            "display_cents",
            "liability_interval",
            "public_base_url",
            "mail_from",
            "backoffice_mail",
            "accounting_start",
            "default_order_name",
            "update_existing_order_names",
            "default_direct_address_name",
            "update_existing_direct_address_names",
        )
