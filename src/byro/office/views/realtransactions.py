from django import forms
from django.contrib import messages
from django.db.models import Q
from django.forms.models import inlineformset_factory
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from byro.bookkeeping.forms import VirtualTransactionForm
from byro.bookkeeping.models import RealTransaction, VirtualTransaction


class RealTransactionListView(ListView):
    template_name = 'office/realtransaction/list.html'
    context_object_name = 'transactions'
    model = RealTransaction

    @property
    def formset_class(self):
        formset_class = inlineformset_factory(
            RealTransaction, VirtualTransaction, form=VirtualTransactionForm,
            can_delete=True, extra=0,
        )
        return formset_class

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)

        for rtrans in ctx['transactions']:
            rtrans.vt_formset = self.formset_class(
                self.request.POST if self.request.method == 'POST' else None,
                queryset=VirtualTransaction.objects.filter(real_transaction=rtrans)
            )

        return ctx
