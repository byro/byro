from django import forms

from byro.common.models import Configuration


class ConfigurationForm(forms.ModelForm):

    class Meta:
        model = Configuration
        fields = (
            'name', 'address', 'url', 'language', 'currency',
            'mail_from', 'liability_interval',
        )
