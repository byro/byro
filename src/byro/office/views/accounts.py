from django import forms
from django.contrib import messages
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from byro.bookkeeping.models import Account, VirtualTransaction

FORM_CLASS = forms.modelform_factory(Account, fields=['name', 'account_category'])


class AccountListView(ListView):
    template_name = 'office/account/list.html'
    context_object_name = 'accounts'
    model = Account


class AccountCreateView(FormView):
    template_name = 'office/account/add.html'
    model = Account
    form_class = FORM_CLASS

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('The member was added, please edit additional details if applicable.'))
        self.form = form
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:accounts.detail', kwargs={'pk': self.form.instance.pk})


class AccountDetailView(ListView):
    template_name = 'office/account/detail.html'
    context_object_name = 'transactions'
    model = VirtualTransaction
    paginate_by = 25

    def get_object(self):
        return Account.objects.get(pk=self.kwargs['pk'])

    def get_queryset(self):
        return self.get_object().transactions.filter(value_datetime__lte=now()).order_by('-value_datetime')

    def get_form(self):
        return FORM_CLASS(instance=self.get_object(), data=self.request.POST if self.request.method == 'post' else None)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['form'] = self.get_form()
        context['account'] = self.get_object()
        return context


class AccountDeleteView(DetailView):
    model = Account
    context_object_name = 'account'
