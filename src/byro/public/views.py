import collections
from datetime import timedelta

from django import forms
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormMixin

from byro.bookkeeping.models import Booking
from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.common.models.configuration import Configuration, MemberViewLevel
from byro.members.models import Member
from byro.office.signals import member_dashboard_tile
from byro.public.forms import PrivacyConsentForm


class MemberBaseView(DetailView):
    slug_field = "profile_memberpage__secret_token"
    slug_url_kwarg = "secret_token"

    model = Member


class MemberView(FormMixin, MemberBaseView):
    template_name = "public/members/dashboard.html"
    form_class = PrivacyConsentForm

    def get_bookings(self, member):
        account_list = [SpecialAccounts.donations, SpecialAccounts.fees_receivable]
        return (
            Booking.objects.with_transaction_data()
            .filter(
                Q(debit_account__in=account_list) | Q(credit_account__in=account_list),
                member=member,
                transaction__value_datetime__lte=now(),
            )
            .order_by("-transaction__value_datetime")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        obj = context["member"]
        config = Configuration.get_solo()

        context["config"] = config
        context["bookings"] = self.get_bookings(obj)
        context["member_view_level"] = MemberViewLevel

        _now = now()
        memberships = obj.memberships.order_by("-start").all()
        if not memberships:
            return context

        member_fields = obj.get_fields()
        for field in context["form"]:
            field.meta = (
                member_fields[field.name].getter(obj)
                if field.name in member_fields
                else ""
            ) or ""
        first = memberships[0].start
        delta = timedelta()
        for ms in memberships:
            delta += (ms.end or _now.date()) - ms.start
            if not ms.end or ms.end <= _now.date():
                context["current_membership"] = ms
        context["memberships"] = memberships
        context["member_since"] = {
            "days": int(delta.total_seconds() / (60 * 60 * 24)),
            "years": int(round(delta.days / 365, 1)),
            "first": first,
        }
        context["tiles"] = []
        for __, response in member_dashboard_tile.send(self.request, member=obj):
            if not response:
                continue
            if isinstance(response, collections.Mapping) and response.get(
                "public", False
            ):
                context["tiles"].append(response)
        return context

    def get_form_kwargs(self, *args, **kwargs):
        result = super().get_form_kwargs(*args, **kwargs)
        result["member"] = self.get_object()
        return result

    def get_success_url(self):
        return reverse(
            "public:memberpage:member.dashboard",
            kwargs={"secret_token": self.kwargs["secret_token"]},
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            form.save()
        return HttpResponseRedirect(self.get_success_url())


class MemberListView(ListView):
    template_name = "public/members/memberlist.html"
    paginate_by = 50
    context_object_name = "members"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        config = Configuration.get_solo()
        context["config"] = config
        context["member_view_level"] = MemberViewLevel
        context["member_undisclosed"] = Member.objects.exclude(
            profile_memberpage__is_visible_to_members=True
        ).count()
        return context

    def get_queryset(self):
        secret_token = self.kwargs.get("secret_token")
        if not secret_token:
            raise Http404("Page does not exist")

        member = Member.all_objects.filter(
            profile_memberpage__secret_token=secret_token
        ).first()
        if not member:
            raise Http404("Page does not exist")

        if not member.is_active:
            raise Http404("Page does not exist")

        return Member.objects.filter(
            profile_memberpage__is_visible_to_members=True
        ).order_by("name")
