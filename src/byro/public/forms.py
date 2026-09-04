from django import forms
from django.utils.translation import gettext_lazy as _

from byro.mails.pgp import normalize_fingerprint
from byro.mails.registration import (
    PGP_REGISTRATION_FIELD,
    build_pgp_fingerprint_field,
    get_member_pgp_fingerprint,
)
from byro.public.models import get_proposable_fields, model_field_for


def _serialize(value):
    """Store a cleaned form value as a string that can be re-cleaned later."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _normalize(value):
    """Treat an empty string and None as the same (absent) value."""
    return None if value in (None, "") else value


class MemberChangeProposalForm(forms.Form):
    """Lets a member propose changes to their own contact data. Nothing is
    applied directly – each changed field is stored as a MemberChangeProposal
    that an admin later accepts or rejects."""

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.member = member
        self.proposable_fields = get_proposable_fields(member)
        pending = {p.field_id: p for p in member.change_proposals.all()}

        for field_id, field in self.proposable_fields.items():
            model_field = model_field_for(member, field)
            form_field = model_field.formfield(required=False)
            form_field.label = field.name
            if field_id in pending:
                form_field.initial = pending[field_id].new_value
                form_field.help_text = _(
                    "Currently stored: %(value)s. Your proposed change is "
                    "awaiting confirmation."
                ) % {"value": field.getter(member)}
            else:
                form_field.initial = field.getter(member)
            self.fields[field_id] = form_field

        form_field = build_pgp_fingerprint_field()
        if PGP_REGISTRATION_FIELD in pending:
            form_field.initial = pending[PGP_REGISTRATION_FIELD].new_value
            form_field.help_text = _(
                "Currently stored: %(value)s. Your proposed change is awaiting "
                "confirmation."
            ) % {"value": get_member_pgp_fingerprint(member)}
        else:
            form_field.initial = get_member_pgp_fingerprint(member)
        self.fields[PGP_REGISTRATION_FIELD] = form_field

    def clean_pgp__fingerprint(self):
        value = self.cleaned_data.get(PGP_REGISTRATION_FIELD)
        if not value:
            return ""
        try:
            return normalize_fingerprint(value)
        except ValueError as e:
            raise forms.ValidationError(e)

    def save(self):
        for field_id, field in self.proposable_fields.items():
            proposed = self.cleaned_data.get(field_id)
            current = field.getter(self.member)
            if _normalize(proposed) == _normalize(current):
                self.member.change_proposals.filter(field_id=field_id).delete()
            else:
                self.member.change_proposals.update_or_create(
                    field_id=field_id,
                    defaults={"new_value": _serialize(proposed)},
                )

        proposed = self.cleaned_data.get(PGP_REGISTRATION_FIELD)
        current = get_member_pgp_fingerprint(self.member)
        if _normalize(proposed) == _normalize(current):
            self.member.change_proposals.filter(
                field_id=PGP_REGISTRATION_FIELD
            ).delete()
        else:
            self.member.change_proposals.update_or_create(
                field_id=PGP_REGISTRATION_FIELD,
                defaults={"new_value": _serialize(proposed)},
            )


class PrivacyConsentForm(forms.Form):
    is_visible_to_members = forms.BooleanField(
        label=_(
            "Yes, my data may be shown in the member list, where it will be visible to other members."
        ),
        required=False,
    )

    def __init__(self, *args, member=None, **kwargs):
        initial = kwargs.pop("initial", {})
        initial["is_visible_to_members"] = (
            member.profile_memberpage.is_visible_to_members
        )
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
