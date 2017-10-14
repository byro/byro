from django.forms import ModelForm

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
