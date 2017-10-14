from django import forms

from .models import VirtualTransaction


class VirtualTransactionForm(forms.ModelForm):
    member_name = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if kwargs.get('instance'):
            initial.update({'member_name': kwargs.get('instance').member.name})
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
        widgets = {
            'member': forms.TextInput(attrs={'class': 'member-typeahead'}),
        }
