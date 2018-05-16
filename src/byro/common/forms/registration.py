from collections import OrderedDict

from django import forms
from django.utils.translation import ugettext_lazy as _

from byro.common.models import Configuration
from byro.members.models import Member, FeeIntervals

class RegistrationConfigForm(forms.Form):
    member__number_position = forms.IntegerField(required=False, label=_('Membership number/ID'))
    member__name_position = forms.IntegerField(required=False, label=_('Name'))
    member__address_position = forms.IntegerField(required=False, label=_('Address'))
    member__email_position = forms.IntegerField(required=False, label=_('E-Mail'))
    member__member_contact_type_position = forms.IntegerField(required=False, label=_('Contact type'))
    membership__start_position = forms.IntegerField(required=False, label=_('Join date'))
    membership__start_default = forms.ChoiceField(required=False, label=_('Default join date'),
        choices=((None,'------------'),('today',_('Current day')),('beginning_mongth',_('Beginning of current month')),('beginning_year',_('Beginning of current year'))))
    membership__amount_position = forms.IntegerField(required=False, label=_('Membership fee'))
    membership__amount_default = forms.IntegerField(required=False, label=_('Default membership fee'))
    membership__interval_position = forms.IntegerField(required=False, label=_('Payment interval'))
    membership__interval_default = forms.ChoiceField(required=False, label=_('Default payment interval'), 
        choices=((None,'------------'),)+FeeIntervals.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for profile in Member.profile_classes:
            for field in profile._meta.fields:
                if field.name not in ('id', 'member'):
                    key = '{profile.__name__}__{field.name}_position'.format(profile=profile, field=field)
                    label = '{field_name} ({profile.__name__})'.format(field_name=field.verbose_name or field.name, profile=profile)
                    self.fields[key] = forms.IntegerField(required=False, label=label)
        config = Configuration.get_solo().registration_form or []
        data = {}
        field_sort_order = {}
        for entry in config:
            if 'name' not in entry:
                continue
            data[entry['name']] = entry
        for full_name, field in self.fields.items():
            name, key = full_name.rsplit("_",1)
            entry = data.get(name, {})
            sort_order = entry.get('position', None) or 998
            # Order by:
            #  + Position in form, if set (or 998 as default)
            #  + 'member' fields first
            #  + Name of base field
            #  + 'position' field first
            #  + Name of key
            field_sort_order[field] = (sort_order, 0 if name.startswith("member") else 1, name, key != 'position', key)
            if key in entry:
                field.initial = entry[key]
            if key == 'position':
                field.widget.attrs['placeholder'] = _('Position in form')
            else:
                field.widget.attrs['placeholder'] = '' # FIXME

        print(field_sort_order)
        self.fields = OrderedDict(sorted(self.fields.items(), key=lambda x: field_sort_order.get(x[1], None) or 999))

    def clean(self):
        ret = super().clean()
        positions = [value for (key,value) in ret.items() if key.endswith("_position") and value is not None]
        if not len(list(positions)) == len(set(positions)):
            raise forms.ValidationError('Every position must be unique!')
        return ret

    def save(self):
        data = {}
        for full_name, value in self.cleaned_data.items():
            name, key = full_name.rsplit("_",1)
            data.setdefault(name, {})[key] = value
        data = [dict(name=key, **value) for (key, value) in data.items()]
        config = Configuration.get_solo()
        config.registration_form = list(data)
        config.save()
