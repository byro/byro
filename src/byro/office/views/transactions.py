from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView
from django_select2.forms import Select2Widget

from byro.bookkeeping.models import (
    Account,
    Booking,
    DocumentTransactionLink,
    Transaction,
)

from .documents import DocumentUploadForm


class NewBookingForm(forms.Form):
    memo = forms.CharField(label=_("Memo"), max_length=1000, required=False)
    member = Booking._meta.get_field("member").formfield(widget=Select2Widget)
    account = Booking._meta.get_field("debit_account").formfield(widget=Select2Widget)
    debit_value = forms.DecimalField(
        min_value=0, max_digits=8, decimal_places=2, required=False
    )
    credit_value = forms.DecimalField(
        min_value=0, max_digits=8, decimal_places=2, required=False
    )


class TransactionDetailView(ListView):
    template_name = "office/transaction/detail.html"
    context_object_name = "bookings"
    model = Transaction
    paginate_by = None

    def get_form(self, input_data=None):
        form = NewBookingForm(input_data)
        form.fields["account"].required = True
        form.fields["member"].required = False
        t = self.get_object()
        if t.balances_credit != t.balances_debit:
            if t.balances_credit > t.balances_debit:
                form.fields["debit_value"].initial = (
                    t.balances_credit - t.balances_debit
                )
            else:
                form.fields["credit_value"].initial = (
                    t.balances_debit - t.balances_credit
                )
        return form

    def get_upload_form(self, input_data=None, input_files=None):
        form = DocumentUploadForm(
            input_data,
            input_files,
            prefix="upload_form",
            initial_category="byro.bookkeeping.receipt",
        )
        form.fields["title"].required = False
        return form

    def get_object(self):
        return Transaction.objects.with_balances().get(pk=self.kwargs["pk"])

    def get_queryset(self):
        return self.get_object().bookings.all()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["transaction"] = self.get_object()
        context["form"] = self.get_form()
        context["upload_form"] = self.get_upload_form()
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        t = self.get_object()
        form = self.get_form(request.POST)
        upload_form = self.get_upload_form(request.POST, request.FILES)

        if upload_form.is_valid():
            self.process_upload_form(upload_form, t)

        if form.is_valid():
            self.process_transaction_changes(form, t)
            t = self.get_object()

            if t.is_balanced:
                if "in_account" in request.GET:
                    account = Account.objects.get(pk=request.GET["in_account"])
                    if account.unbalanced_transactions.count():
                        return redirect(
                            "{}?filter=unbalanced".format(
                                reverse(
                                    "office:finance.accounts.detail",
                                    kwargs={"pk": account.pk},
                                )
                            )
                        )
                return redirect("office:finance.accounts.list")

        if "in_account" in request.GET:
            return redirect(
                "{}?in_account={}".format(
                    reverse("office:finance.transactions.detail", kwargs={"pk": t.pk}),
                    request.GET["in_account"],
                )
            )
        else:
            return redirect("office:finance.transactions.detail", pk=t.pk)

    def process_transaction_changes(self, form, t):
        arguments = dict(
            memo=form.cleaned_data["memo"],
            account=form.cleaned_data["account"],
            member=form.cleaned_data["member"],
            importer="_manual_entry",
            user_or_context=self,
        )
        if form.cleaned_data["debit_value"]:
            t.debit(amount=form.cleaned_data["debit_value"], **arguments)
        if form.cleaned_data["credit_value"]:
            t.credit(amount=form.cleaned_data["credit_value"], **arguments)
        t.save()
        messages.success(self.request, _("The transaction was updated."))
        t.log(self, ".updated")

    def process_upload_form(self, form, t):
        form.save()
        DocumentTransactionLink.objects.create(transaction=t, document=form.instance)
        t.log(
            self,
            ".document.created",
            document=form.instance,
            content_hash=form.instance.content_hash,
        )
