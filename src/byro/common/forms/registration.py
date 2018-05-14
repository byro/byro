from collections import OrderedDict

from django import forms
from django.utils.translation import ugettext_lazy as _

from byro.common.models import Configuration
from byro.members.models import Member


class RegistrationConfigForm(forms.Form):
    member__number = forms.IntegerField(required=False, label=_('Membership number/ID'))
    member__name = forms.IntegerField(required=False, label=_('Name'))
    member__address = forms.IntegerField(required=False, label=_('Address'))
    member__email = forms.IntegerField(required=False, label=_('E-Mail'))
    member__member_contact_type = forms.IntegerField(required=False, label=_('Contact type'))
    membership__start = forms.IntegerField(required=False, label=_('Join date'))
    membership__amount = forms.IntegerField(required=False, label=_('Membership fee'))
    membership__interval = forms.IntegerField(required=False, label=_('Payment interval'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for profile in Member.profile_classes:
            for field in profile._meta.fields:
                if field.name not in ('id', 'member'):
                    key = '{profile.__name__}__{field.name}'.format(profile=profile, field=field)
                    label = '{field_name} ({profile.__name__})'.format(field_name=field.verbose_name or field.name, profile=profile)
                    self.fields[key] = forms.IntegerField(required=False, label=label)
        config = Configuration.get_solo().registration_form or []
        for entry in config:
            field = self.fields.get(entry['name'])
            if field:
                field.initial = entry['position']
        self.fields = OrderedDict(sorted(self.fields.items(), key=lambda x: getattr(x[1], 'initial', None) or 999))
        for field in self.fields.values():
            field.widget.attrs['placeholder'] = _('Position in form')

    def clean(self):
        ret = super().clean()
        values = [value for value in self.cleaned_data.values() if value is not None]
        if not len(list(values)) == len(set(values)):
            raise forms.ValidationError('Every position must be unique!')
        return ret

    def save(self):
        data = [
            {
                'position': value,
                'name': key,
            }
            for key, value in self.cleaned_data.items()
        ]
        config = Configuration.get_solo()
        config.registration_form = list(data)
        config.save()
