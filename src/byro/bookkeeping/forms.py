from django import forms

from .models import VirtualTransaction


class VirtualTransactionForm(forms.ModelForm):
    member_name = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        if kwargs.get('instance') and kwargs.get('instance').member:
            initial.update({'member_name': kwargs.get('instance').member.name})
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        self.fields['source_account'].required = False
        self.fields['destination_account'].required = False
        self.fields['member'].required = False
        self.fields['amount'].required = False

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
