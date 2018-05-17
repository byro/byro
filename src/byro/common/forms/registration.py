from collections import OrderedDict
from decimal import Decimal

from django import forms
from django.db import models
from django.utils.decorators import classproperty
from django.utils.translation import ugettext_lazy as _

from byro.common.models import Configuration
from byro.members.models import Member, Membership, FeeIntervals

class DefaultDates:
    TODAY = 'today'
    BEGINNING_MONTH = 'beginning_month'
    BEGINNING_YEAR = 'beginning_year'
    FIXED_DATE = 'fixed_date'

    @classproperty
    def choices(cls):
        return (
            (None, '------------'),
            (cls.TODAY, _('Current day')),
            (cls.BEGINNING_MONTH, _('Beginning of current month')),
            (cls.BEGINNING_YEAR, _('Beginning of current year')),
            (cls.FIXED_DATE, _('Other/fixed date')),
        )

class DefaultBoolean:
    @classproperty
    def choices(cls):
        return (
            (None, '------------'),
            (False, _('False')),
            (True, _('True')),
        )

SPECIAL_NAMES = {
    Member: 'member',
    Membership: 'membership',
}
SPECIAL_ORDER = [
    'member__number',
    'member__name',
    'member__address',
    'member__email',
    'membership__start',
    'membership__interval',
    'membership__amount',
]

class RegistrationConfigForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields_extra = OrderedDict()
        field_data = []
        config = Configuration.get_solo().registration_form or []
        data = {}
        for entry in config:
            if 'name' not in entry:
                continue
            data[entry['name']] = entry
        for model in [Member, Membership] + Member.profile_classes:
            for field in model._meta.fields:
                if field.name in ('id', 'member'):
                    continue
                if model is Member and field.name in ('membership_type', ):
                    continue

                key = '{}__{}'.format(SPECIAL_NAMES.get(model, model.__name__), field.name)
                entry = data.get(key, {})

                verbose_name = field.verbose_name or field.name
                if model not in SPECIAL_NAMES:
                    verbose_name = '{verbose_name} ({model.__name__})'.format(verbose_name=verbose_name, model=model)
                form_fields = OrderedDict()

                position_field = forms.IntegerField(required=False, label=_("Position in form"))
                form_fields['{}__position'.format(key)] = position_field

                if isinstance(field, models.DateField):
                    form_fields['{}__default_date'.format(key)] = forms.ChoiceField(required=False, label=_('Default date'), choices=DefaultDates.choices)

                default_field = None
                choices = getattr(field, 'choices', None)
                if choices:
                    default_field = forms.ChoiceField(
                        required=False, 
                        label=_('Default value'),
                        choices=[(None, '-----------')]+list(choices))
                elif not(model is Member and field.name == 'number'):
                    if isinstance(field, models.BooleanField):
                        form_fields['{}__default_boolean'.format(key)] = forms.ChoiceField(required=False,
                            label=_('Default value'),
                            choices=DefaultBoolean.choices)
                    elif isinstance(field, models.CharField):
                        default_field = forms.CharField(required=False,
                            label=_('Default value'))
                    elif isinstance(field, models.DecimalField):
                        default_field = forms.DecimalField(required=False, 
                            label=_('Default value'), 
                            max_digits=field.max_digits,
                            decimal_places=field.decimal_places)
                    elif isinstance(field, models.DateField):
                        default_field = forms.CharField(required=False,
                            label=_('Other/fixed date'))

                if default_field:
                    form_fields['{}__default'.format(key)] = default_field

                for full_name, form_field in form_fields.items():
                    value_name = full_name.rsplit('__',1)[-1]
                    form_field.initial = entry.get(value_name, form_field.initial) 

                field_data.append((
                    data.get(key, {}).get('position', None) or 998,
                    SPECIAL_ORDER.index(key) if key in SPECIAL_ORDER else 66,
                    0 if model in SPECIAL_NAMES else 1,
                    key,
                    verbose_name,
                    form_fields
                ))

        # Sort model fields, by:
        #  + Position in form, if set (use 998 as default)
        #  + SPECIAL_ORDER first
        #  + SPECIAL_NAMES first
        #  + key ({model.name}__{field.name})
        field_data.sort()

        for _ignore, _ignore, _ignore, key, verbose_name, form_fields in field_data:
            self.fields_extra[key] = (verbose_name, (self[name] for name in form_fields.keys()))
            self.fields.update(form_fields)

    def clean(self):
        ret = super().clean()
        positions = [value for (key,value) in ret.items() if key.endswith("__position") and value is not None]
        if not len(list(positions)) == len(set(positions)):
            raise forms.ValidationError('Every position must be unique!')
        return ret

    def save(self):
        data = {}
        for full_name, value in self.cleaned_data.items():
            name, key = full_name.rsplit("__",1)
            if not (value == "" or value is None):
                if isinstance(value, Decimal):
                    value = str(value)
                if key == 'default_boolean':
                    value = bool(value == 'True')
                data.setdefault(name, {})[key] = value
        data = [dict(name=key, **value) for (key, value) in data.items()]
        config = Configuration.get_solo()
        config.registration_form = list(data)
        config.save()
