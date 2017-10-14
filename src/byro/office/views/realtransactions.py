from django import forms
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from byro.bookkeeping.models import RealTransaction


class RealTransactionListView(ListView):
    template_name = 'office/realtransaction/list.html'
    context_object_name = 'transactions'
    model = RealTransaction
