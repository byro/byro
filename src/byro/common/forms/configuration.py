from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from i18nfield.strings import LazyI18nString

from byro.common.forms.i18n import RestrictedLanguagesI18nModelForm
from byro.common.models import Configuration
from byro.mails import default
from byro.mails.footer import check_member_mail_footer, get_member_mail_footer
from byro.members.models import Member


class InitialForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    class Meta:
        model = Configuration
        fields = ("name", "backoffice_mail", "mail_from")


class ConfigurationForm(RestrictedLanguagesI18nModelForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            # Browsers send the line breaks of a text area as CRLF. Compared
            # with the stored text, the footer would be changed on every save.
            prefix = self.add_prefix("member_mail_footer") + "_"
            self.data = self.data.copy()
            for key in [key for key in self.data if key.startswith(prefix)]:
                self.data[key] = self.data[key].replace("\r\n", "\n")
        if get_member_mail_footer(self.instance) is None:
            # Show the built-in default that is in effect, so that saving the
            # form does not remove it.
            self.initial["member_mail_footer"] = default.MEMBER_MAIL_FOOTER

    def clean_member_mail_footer(self):
        """Change only the language that was edited.

        The form shows one language. Its text replaces the stored one, the
        other languages are kept. A footer that is emptied is removed in every
        language: the other languages would otherwise be used in its place.
        """
        stored = get_member_mail_footer(self.instance)
        if "member_mail_footer" not in self.changed_data:
            return stored
        # The field has every language, the ones that are not shown are empty.
        shown = self.fields["member_mail_footer"].widget.enabled_locales
        footer = self.cleaned_data["member_mail_footer"]
        edited = {locale: footer.data.get(locale) or "" for locale in shown}
        if not any(text.strip() for text in edited.values()):
            return LazyI18nString({})
        for text in edited.values():
            if text.strip():
                check_member_mail_footer(text, self.instance)
        if stored is not None and isinstance(stored.data, dict):
            texts = dict(stored.data)
        else:
            texts = {
                locale: default.MEMBER_MAIL_FOOTER.data[locale]
                for locale, _name in settings.LANGUAGES
            }
        texts.update(edited)
        return LazyI18nString(texts)

    def get_additional_log_changes(self, original_values):
        """Log the footer in every language: as text it would be shown in the
        language of the request, which need not be the one that was edited."""
        if "member_mail_footer" not in self.changed_data:
            return {}
        # a LazyI18nString, without data for NULL
        original = original_values.get("member_mail_footer")
        return {
            "member_mail_footer": (
                getattr(original, "data", None),
                self.cleaned_data["member_mail_footer"].data,
            )
        }

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
            "member_mail_footer",
            "accounting_start",
            "default_order_name",
            "update_existing_order_names",
            "default_direct_address_name",
            "update_existing_direct_address_names",
        )
