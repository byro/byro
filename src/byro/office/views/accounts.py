from django import forms
from django.contrib import messages
from django.db import models
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from byro.bookkeeping.models import Account, AccountCategory, Transaction

FORM_CLASS = forms.modelform_factory(Account, fields=["name", "account_category"])

ACCOUNT_COLUMN_HEADERS = {
    # FIXME Check this with an accountant who is a native english speaker
    AccountCategory.INCOME: (_("Charge"), _("Revenue")),
    AccountCategory.ASSET: (_("Increase"), _("Decrease")),
    AccountCategory.EQUITY: (_("Decrease"), _("Increase")),
    AccountCategory.LIABILITY: (_("Decrease"), _("Increase")),
    AccountCategory.EXPENSE: (_("Expense"), _("Rebate")),
}


class AccountListView(ListView):
    template_name = "office/account/list.html"
    context_object_name = "accounts"
    model = Account


class AccountCreateView(FormView):
    template_name = "office/account/add.html"
    model = Account
    form_class = FORM_CLASS

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            _("The account was added, please edit additional details if applicable."),
        )
        self.form = form
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "office:finance.accounts.detail", kwargs={"pk": self.form.instance.pk}
        )


class AccountDetailView(ListView):
    template_name = "office/account/detail.html"
    context_object_name = "bookings"
    model = Transaction
    paginate_by = 25

    def get_object(self):
        if not hasattr(self, "object"):
            self.object = Account.objects.get(pk=self.kwargs["pk"])
        return self.object

    def get_queryset(self):
        qs = self.get_object().bookings_with_transaction_data
        if self.request.GET.get("filter") == "unbalanced":
            qs = qs.exclude(
                transaction_balances_debit=models.F("transaction_balances_credit")
            )
        qs = qs.filter(transaction__value_datetime__lte=now()).order_by(
            "-transaction__value_datetime"
        )
        return qs

    def get_form(self, request=None):
        form = FORM_CLASS(request.POST if request else None, instance=self.get_object())
        form.fields["account_category"].disabled = True
        return form

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["form"] = self.get_form()
        context["account"] = self.get_object()
        context["ACCOUNT_COLUMN_HEADERS"] = ACCOUNT_COLUMN_HEADERS.get(
            self.get_object().account_category, (_("Debit"), _("Credit"))
        )
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form(request)
        if form.is_valid() and form.has_changed():
            form.save()
            messages.success(self.request, _("Your changes have been saved."))
        return redirect(reverse("office:finance.accounts.detail", kwargs=self.kwargs))


class AccountDeleteView(DetailView):
    model = Account
    context_object_name = "account"
