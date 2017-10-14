from django import forms

from .models import VirtualTransaction


class VirtualTransactionForm(forms.ModelForm):
    member = forms.CharField(widget=forms.TextInput(attrs={'class': 'member-typeahead'}))

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if kwargs.get('instance'):
            initial.update({'member': kwargs.get('instance').member.name})
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    class Meta:
        model = VirtualTransaction
        fields = [
            'source_account',
            'destination_account',
            'member',
            'amount',
        ]
