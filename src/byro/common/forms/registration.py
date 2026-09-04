from collections import OrderedDict
from decimal import Decimal

from django import forms
from django.db import models
from django.db.models.fields import NOT_PROVIDED
from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _

from byro.common.models import Configuration
from byro.mails.registration import PGP_REGISTRATION_FIELD, build_pgp_fingerprint_field
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
# Fields offered in the registration form as long as nothing has been configured.
DEFAULT_FIELDS = list(SPECIAL_ORDER)


def get_field_key(model, field):
    return f"{SPECIAL_NAMES.get(model, model.__name__)}__{field.name}"


def is_mandatory_field(field):
    """Return True if a new member cannot be saved without a value for ``field``.

    This mirrors what happens when a model instance is saved without the
    attribute being set: a NOT NULL column without a (database) default that
    does not fall back to the empty string ends up as NULL and violates the
    database constraint.
    """
    return (
        field.editable
        and not field.primary_key
        and not field.null
        and not field.empty_strings_allowed
        and not field.has_default()
        and getattr(field, "db_default", NOT_PROVIDED) is NOT_PROVIDED
    )


def get_mandatory_fields():
    """Return the keys of all fields that always have to be part of the
    registration form, ordered like ``SPECIAL_ORDER``."""
    keys = [
        get_field_key(model, field)
        for model, field in RegistrationConfigForm.get_form_fields()
        if is_mandatory_field(field)
    ]
    return sorted(
        keys,
        key=lambda key: (
            SPECIAL_ORDER.index(key) if key in SPECIAL_ORDER else len(SPECIAL_ORDER),
            key,
        ),
    )


def get_default_entries():
    """Return the configuration shown when no registration form has been
    saved yet, keyed by field name."""
    entries = {
        key: {"name": key, "position": index + 1}
        for index, key in enumerate(DEFAULT_FIELDS)
    }
    entries["membership__start"]["default_date"] = DefaultDates.BEGINNING_MONTH
    return entries


class RegistrationConfigForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields_extra = OrderedDict()
        fieldsets = []
        config = Configuration.get_solo().registration_form or []
        data = {entry["name"]: entry for entry in config if "name" in entry}
        if not data:
            data = get_default_entries()

        # Mandatory fields missing from the stored configuration are appended
        # to the end of the current form, so they can neither be left out by
        # older configurations nor by removing them client-side.
        mandatory = get_mandatory_fields()
        positions = {}
        next_position = (
            max((entry.get("position") or 0 for entry in data.values()), default=0) + 1
        )
        for key in mandatory:
            if not data.get(key, {}).get("position"):
                positions[key] = next_position
                next_position += 1

        for model, field in self.get_form_fields():
            key = get_field_key(model, field)
            entry = data.get(key, {})
            position = entry.get("position") or positions.get(key)

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
            fields["position"].initial = position

            fieldsets.append(
                (
                    (  # This part is responsible for sorting the model fields:
                        position or 998,  # Position in form, if set (or 998)
                        (
                            SPECIAL_ORDER.index(key) if key in SPECIAL_ORDER else 66
                        ),  # SPECIAL_ORDER first
                        0 if model in SPECIAL_NAMES else 1,  # SPECIAL_NAMES first
                    ),
                    key,  # Fall back to sorting by key, otherwise
                    verbose_name,
                    OrderedDict(
                        (
                            f"{key}__{name}",
                            value,
                        )  # TODO: make fields an ordered dict that prepends {key} to every key for more fanciness
                        for name, value in fields.items()
                    ),
                    key in mandatory,
                )
            )

        pgp_entry = data.get(PGP_REGISTRATION_FIELD, {})
        position_field = forms.IntegerField(
            required=False,
            label=_("Position in form"),
            initial=pgp_entry.get("position"),
        )
        fieldsets.append(
            (
                (pgp_entry.get("position", None) or 998, 80, 1),
                PGP_REGISTRATION_FIELD,
                build_pgp_fingerprint_field().label,
                OrderedDict(
                    (
                        (
                            f"{PGP_REGISTRATION_FIELD}__position",
                            position_field,
                        ),
                    )
                ),
                False,
            )
        )

        fieldsets.sort()
        for _position, key, verbose_name, form_fields, is_mandatory in fieldsets:
            self.fields_extra[key] = (
                verbose_name,
                (self[name] for name in form_fields.keys()),
                is_mandatory,
            )
            self.fields.update(form_fields)

    @staticmethod
    def get_form_fields():
        for model in [Member, Membership] + Member.profile_classes:
            for field in model._meta.fields:
                if field.name in ("id", "member") or (
                    model is Member
                    and field.name
                    in ["membership_type", "direct_address_name", "order_name"]
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
        if len(positions) != len(set(positions)):
            self.add_error(None, _("Every position must be unique!"))

        # The position inputs are hidden client-side, so errors about them
        # have to be reported as non-field errors to be visible at all.
        missing = [
            str(self.fields_extra[key][0])
            for key in get_mandatory_fields()
            if ret.get(f"{key}__position") is None
        ]
        if missing:
            self.add_error(
                None,
                _(
                    "These fields are required and have to be part of the registration form: %(fields)s"
                )
                % {"fields": ", ".join(missing)},
            )
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
