from django import forms
from django.db.models.fields.related import OneToOneRel
from django.utils.translation import ugettext_lazy as _

from byro.common.models import Configuration
from byro.members.models import Member


class RegistrationConfigForm(forms.Form):
    number = forms.IntegerField(required=False, label=_('Membership number/ID'))
    name = forms.IntegerField(required=False, label=_('Name'))
    address = forms.IntegerField(required=False, label=_('Address'))
    email = forms.IntegerField(required=False, label=_('E-Mail'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile_classes = [
            related.related_model for related in Member._meta.related_objects
            if isinstance(related, OneToOneRel) and related.name.startswith('profile_')
        ]
        for profile in profile_classes:
            for field in profile._meta.fields:
                if field.name not in ('id', 'member'):
                    self.fields[f'{profile.__name__}__{field.name}'] = forms.IntegerField(required=False, label=f'{field.verbose_name or field.name} ({profile.__name__})')
        config = Configuration.get_solo().registration_form or []
        for entry in config:
            field = self.fields.get(entry['name'])
            if field:
                field.initial = entry['position']

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
