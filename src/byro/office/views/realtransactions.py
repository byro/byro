from django.forms.models import BaseModelFormSet, inlineformset_factory
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import ListView

from byro.bookkeeping.forms import VirtualTransactionForm
from byro.bookkeeping.models import RealTransaction, VirtualTransaction


class RealTransactionListView(ListView):
    template_name = 'office/realtransaction/list.html'
    context_object_name = 'transactions'
    paginate_by = 25
    model = RealTransaction

    def get_queryset(self):
        qs = super().get_queryset().order_by('-value_datetime')
        if self.request.GET.get('filter') == 'matched':
            qs = qs.filter(virtual_transactions__isnull=False)
        elif self.request.GET.get('filter') == 'unmatched':
            qs = qs.filter(virtual_transactions__isnull=True)
        year = self.request.GET.get('year')
        if year is not None and year.isdigit():
            qs = qs.filter(value_datetime__year=year)
        return qs

    def post(self, request, *args, **kwargs):
        try:
            realtransaction_id = request.POST['realtransaction_id']
        except LookupError:
            return HttpResponseBadRequest()

        formset = self.get_formset(realtransaction_id)

        if formset.is_valid():
            formset.save()
        else:
            # TODO: messages
            raise Exception('invalid data')

        return HttpResponseRedirect(reverse('office:realtransactions.list'))

    @cached_property
    def formset_class(self):
        formset_class = inlineformset_factory(
            RealTransaction, VirtualTransaction, form=VirtualTransactionForm,
            formset=BaseModelFormSet, can_delete=True, extra=0,
        )
        return formset_class

    def get_formset(self, real_transaction_id):
        return self.formset_class(
            self.request.POST if self.request.method == 'POST' else None,
            queryset=VirtualTransaction.objects.filter(real_transaction_id=real_transaction_id),
            prefix=f'virtual_transactions_{real_transaction_id}',
        )

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        for transaction in ctx['transactions']:
            transaction.vt_formset = self.get_formset(transaction.pk)
        return ctx
