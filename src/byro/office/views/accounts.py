from django import forms
from django.views.generic import DetailView, FormView, ListView

from byro.bookkeeping.models import Account


class AccountListView(ListView):
    template_name = 'office/account/list.html'
    model = Account


class AccountCreateView(FormView):
    template_name = 'office/account/add.html'
    model = Account
    form_class = forms.modelform_factory(Account, fields=['name', 'account_category'])


class AccountDetailView(DetailView):
    template_name = 'office/account/detail.html'
    model = Account


class AccountDeleteView(DetailView):
    model = Account
