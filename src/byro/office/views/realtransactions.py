from django.db.models import Q
from django.forms.models import BaseModelFormSet, inlineformset_factory
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import ListView, TemplateView

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
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(Q(purpose__icontains=search) | Q(originator__icontains=search))
        return qs


class RealTransactionMatchView(TemplateView):
    template_name = 'office/realtransaction/match.html'

    def get_queryset(self):
        qs = RealTransaction.objects.all().order_by('-value_datetime')
        ids = self.request.GET.getlist('ids')
        qs = qs.filter(id__in=ids)
        return qs

    def post(self, request, *args, **kwargs):
        formset = self.get_formset()
        if formset.is_valid():
            for transaction in self.get_queryset():
                for form in formset:
                    if form.instance:
                        VirtualTransaction.objects.create(
                            real_transaction=transaction,
                            value_datetime=transaction.value_datetime,
                            source_account=form.instance.source_account,
                            destination_account=form.instance.destination_account,
                            member=form.instance.member,
                            amount=form.instance.amount or transaction.amount,
                        )
        else:
            # TODO: messages
            raise Exception('invalid data: ' + str(formset.errors))

        return HttpResponseRedirect(reverse('office:realtransactions.list'))

    @cached_property
    def formset_class(self):
        formset_class = inlineformset_factory(
            RealTransaction, VirtualTransaction, form=VirtualTransactionForm,
            formset=BaseModelFormSet, can_delete=True, extra=0,
        )
        return formset_class

    def get_formset(self):
        return self.formset_class(
            self.request.POST if self.request.method == 'POST' else None,
            queryset=VirtualTransaction.objects.none(),
        )

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['transactions'] = self.get_queryset()
        ctx['formset'] = self.get_formset()
        return ctx
