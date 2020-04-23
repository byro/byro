from django import forms
from django.utils.translation import ugettext_lazy as _


class PrivacyConsentForm(forms.Form):
    is_visible_to_members = forms.BooleanField(
        label=_(
            "Yes, my data may be shown in the member list, where it will be visible to other members."
        ),
        required=False,
    )

    def __init__(self, *args, member=None, **kwargs):
        initial = kwargs.pop("initial", {})
        initial[
            "is_visible_to_members"
        ] = member.profile_memberpage.is_visible_to_members
        super().__init__(*args, initial=initial, **kwargs)
        self.member = member

        blocked = [
            "sepa",
            "secret",
            "balance",
            "active",
            "_internal_id",
            "memberpage",
            "memberships.last",
        ]

        for key, value in member.get_fields().items():
            if (
                any(b in value.path for b in blocked)
                or any(key in b for b in blocked)
                or key == "pk"
            ):
                continue
            self.fields[key] = forms.BooleanField(
                required=False,
                label=value.name,
                initial=self.member.profile_memberpage.publication_consent.get(
                    "fields", {}
                )
                .get(key, {})
                .get("visibility"),
            )

    def save(self):
        data = self.cleaned_data
        result = {}
        for key in self.member.get_fields():
            if data.get(key):
                result[key] = {"visibility": "share"}
        self.member.profile_memberpage.publication_consent = {"fields": result}
        self.member.profile_memberpage.is_visible_to_members = data[
            "is_visible_to_members"
        ]
        self.member.profile_memberpage.save()
