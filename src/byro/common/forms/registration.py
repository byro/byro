from collections import OrderedDict
from decimal import Decimal

from django import forms
from django.db import models
from django.utils.decorators import classproperty
from django.utils.translation import ugettext_lazy as _

from byro.common.models import Configuration
from byro.members.models import Member, Membership


class DefaultDates:
    TODAY = "today"
    BEGINNING_MONTH = "beginning_month"
    BEGINNING_MONTH_NEXT = "beginning_month_next"
    BEGINNING_YEAR = "beginning_year"
    BEGINNING_YEAR_NEXT = "beginning_year_next"
    FIXED_DATE = "fixed_date"

    @classproperty
    def choices(cls):
        return (
            (None, "------------"),
            (cls.TODAY, _("Current day")),
            (cls.BEGINNING_MONTH, _("Beginning of current month")),
            (cls.BEGINNING_MONTH_NEXT, _("Beginning of next month")),
            (cls.BEGINNING_YEAR, _("Beginning of current year")),
            (cls.BEGINNING_YEAR_NEXT, _("Beginning of next year")),
            (cls.FIXED_DATE, _("Other/fixed date")),
        )


class DefaultBoolean:
    @classproperty
    def choices(cls):
        return ((None, "------------"), (False, _("False")), (True, _("True")))


SPECIAL_NAMES = {Member: "member", Membership: "membership"}
SPECIAL_ORDER = [
    "member__number",
    "member__name",
    "member__address",
    "member__email",
    "membership__start",
    "membership__interval",
    "membership__amount",
]


class RegistrationConfigForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields_extra = OrderedDict()
        fieldsets = []
        config = Configuration.get_solo().registration_form or []
        data = {entry["name"]: entry for entry in config if "name" in entry}

        for model, field in self.get_form_fields():

            key = "{}__{}".format(SPECIAL_NAMES.get(model, model.__name__), field.name)
            entry = data.get(key, {})

            verbose_name = field.verbose_name or field.name
            if model not in SPECIAL_NAMES:
                verbose_name = "{verbose_name} ({model.__name__})".format(
                    verbose_name=verbose_name, model=model
                )

            fields = OrderedDict()
            fields["position"] = forms.IntegerField(
                required=False, label=_("Position in form")
            )
            if isinstance(field, models.DateField):
                fields["default_date"] = forms.ChoiceField(
                    required=False,
                    label=_("Default date"),
                    choices=DefaultDates.choices,
                )
            if isinstance(field, models.BooleanField):
                fields["default_boolean"] = forms.ChoiceField(
                    required=False,
                    label=_("Default value"),
                    choices=DefaultBoolean.choices,
                )
            default_field = self.build_default_field(field, model)
            if default_field:
                fields["default"] = default_field
            for name, form_field in fields.items():
                form_field.initial = entry.get(name, form_field.initial)

            fieldsets.append(
                (
                    (  # This part is responsible for sorting the model fields:
                        data.get(key, {}).get("position", None)
                        or 998,  # Position in form, if set (or 998)
                        SPECIAL_ORDER.index(key)
                        if key in SPECIAL_ORDER
                        else 66,  # SPECIAL_ORDER first
                        0 if model in SPECIAL_NAMES else 1,  # SPECIAL_NAMES first
                    ),
                    key,  # Fall back to sorting by key, otherwise
                    verbose_name,
                    OrderedDict(
                        (
                            "{key}__{name}".format(key=key, name=name),
                            value,
                        )  # TODO: make fields an ordered dict that prepends {key} to every key for more fanciness
                        for name, value in fields.items()
                    ),
                )
            )

        fieldsets.sort()
        for _position, key, verbose_name, form_fields in fieldsets:
            self.fields_extra[key] = (
                verbose_name,
                (self[name] for name in form_fields.keys()),
            )
            self.fields.update(form_fields)

    @staticmethod
    def get_form_fields():
        for model in [Member, Membership] + Member.profile_classes:
            for field in model._meta.fields:
                if field.name in ("id", "member") or (
                    model is Member and field.name == "membership_type"
                ):
                    continue
                yield (model, field)

    def build_default_field(self, field, model):
        choices = getattr(field, "choices", None)
        if choices:
            return forms.ChoiceField(
                required=False,
                label=_("Default value"),
                choices=[(None, "-----------")] + list(choices),
            )
        if not (model is Member and field.name == "number"):
            if isinstance(field, models.CharField):
                return forms.CharField(required=False, label=_("Default value"))
            elif isinstance(field, models.DecimalField):
                return forms.DecimalField(
                    required=False,
                    label=_("Default value"),
                    max_digits=field.max_digits,
                    decimal_places=field.decimal_places,
                )
            elif isinstance(field, models.DateField):
                return forms.CharField(required=False, label=_("Other/fixed date"))

    def clean(self):
        ret = super().clean()
        positions = [
            value
            for (key, value) in ret.items()
            if key.endswith("__position") and value is not None
        ]
        if not len(list(positions)) == len(set(positions)):
            raise forms.ValidationError("Every position must be unique!")
        return ret

    def save(self):
        data = {}
        for full_name, value in self.cleaned_data.items():
            name, key = full_name.rsplit("__", 1)
            if not (value == "" or value is None):
                if isinstance(value, Decimal):
                    value = str(value)
                if key == "default_boolean":
                    value = bool(value == "True")
                data.setdefault(name, {})[key] = value
        data = [dict(name=key, **value) for (key, value) in data.items()]
        config = Configuration.get_solo()
        config.registration_form = list(data)
        config.save()
