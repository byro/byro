from django.forms import ModelForm, TextInput

from .models import VirtualTransaction


class VirtualTransactionForm(ModelForm):

    class Meta:
        model = VirtualTransaction
        fields = [
            'source_account',
            'destination_account',
            'member',
            'amount',
        ]
        widgets = {
            'member': TextInput(attrs={'class': 'data-member-typeahead'}),
        }
