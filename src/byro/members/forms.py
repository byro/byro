from datetime import timedelta

from django import forms
from django.db.models.fields.related import OneToOneRel
from django.utils.timezone import now

from byro.common.forms.registration import DefaultDates
from byro.common.models import Configuration
from byro.members.models import Member, Membership, get_next_member_number

MAPPING = {"member": Member, "membership": Membership}


class CreateMemberForm(forms.Form):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        config = Configuration.get_solo().registration_form or []
        config = sorted(
            [field for field in config if field["position"] is not None],
            key=lambda field: field["position"],
        )
        profiles = {
            profile.related_model.__name__: profile.related_model
            for profile in Member._meta.related_objects
            if isinstance(profile, OneToOneRel) and profile.name.startswith("profile_")
        }
        for field in config:
            self.build_field(field, profiles)

        if "member__number" in self.fields:
            self.fields["member__number"].initial = get_next_member_number()

    def get_date_initial(self, field):
        today = now().date()
        default = field["default_date"]
        if default == DefaultDates.TODAY:
            return today
        elif default == DefaultDates.BEGINNING_MONTH:
            return today.replace(day=1)
        elif default == DefaultDates.BEGINNING_MONTH_NEXT:
            return (today.replace(day=28) + timedelta(days=7)).replace(day=1)
        elif default == DefaultDates.BEGINNING_YEAR:
            return today.replace(day=1, month=1)
        elif default == DefaultDates.BEGINNING_YEAR_NEXT:
            return (today.replace(day=31, month=12) + timedelta(days=7)).replace(
                day=1, month=1
            )
        elif default == DefaultDates.FIXED_DATE:
            return field.get("default", None)

    def build_field(self, field, profiles):
        model_name = field["name"].split("__")[0]
        if model_name in MAPPING:
            model = MAPPING[model_name]
        else:
            model = profiles[field["name"].split("__")[0]]
        form_field = model._meta.get_field(field["name"].split("__")[-1]).formfield()
        form_field.model = model
        self.fields[field["name"]] = form_field
        if "default_date" in field:
            form_field.initial = self.get_date_initial(field=field)
        elif "default_boolean" in field:
            form_field.initial = field["default_boolean"]
        elif "default" in field:
            form_field.initial = field["default"]

    def save(self):
        profiles = {
            profile.related_model.__name__: profile.related_model()
            for profile in Member._meta.related_objects
            if isinstance(profile, OneToOneRel) and profile.name.startswith("profile_")
        }
        member = Member()
        membership = Membership()

        for key, value in self.cleaned_data.items():
            model_name = key.split("__")[0]
            if model_name == "member":
                obj = member
            elif model_name == "membership":
                obj = membership
            else:
                obj = profiles[key.split("__")[0]]
            setattr(obj, key.split("__", maxsplit=1)[-1], value)
        member.save()
        member.refresh_from_db()
        membership.member = self.instance = member
        membership.save()
        for profile in profiles.values():
            profile.member = member
            profile.save()
