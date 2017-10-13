from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from byro.members.forms import CreateMemberForm
from byro.members.models import Member


class MemberListView(ListView):
    template_name = 'office/member/list.html'
    context_object_name = 'members'
    model = Member


class MemberCreateView(FormView):
    template_name = 'office/member/add.html'
    form_class = CreateMemberForm

    def get_object(self):
        return Member.objects.get(pk=self.kwargs['pk'])

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('The member was added, please edit additional details if applicable.'))
        self.form = form
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:members.detail', kwargs={'pk': self.form.instance.pk})


class MemberDashboardView(DetailView):
    template_name = 'office/member/dashboard.html'
    context_object_name = 'member'
    model = Member

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        obj = self.get_object()
        delta = now().date() - obj.memberships.first().start
        context['member_since'] = {
            'days': int(delta.total_seconds() / (60 * 60 * 24)),
            'years': round(delta.days / 365, 1),
        }
        return context


class MemberDataView(DetailView):
    template_name = 'office/member/data.html'
    context_object_name = 'member'
    model = Member

    def _instantiate(self, form_class, member, profile_class=None):
        params = {
            'instance': getattr(member, profile_class._meta.get_field('member').related_query_name()) if profile_class else member,
            'prefix': profile_class.__name__ if profile_class else 'member_',
            'data': self.request.POST if self.request.method == 'POST' else None,
        }
        return form_class(**params)

    def get_forms(self):
        obj = self.get_object()
        return [self._instantiate(forms.modelform_factory(Member, fields=['name', 'number', 'address', 'email']), obj)] + [
            self._instantiate(forms.modelform_factory(
                profile_class,
                fields=[f.name for f in profile_class._meta.fields if f.name not in ['id', 'member']],
            ), obj, profile_class)
            for profile_class in obj.profile_classes
        ]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['forms'] = self.get_forms()
        return context

    def post(self, *args, **kwargs):
        for form in self.get_forms():
            if form.is_valid():
                form.save()
        messages.success(self.request, _('Your changes have been saved.'))
        return redirect(reverse('office:members.data', kwargs=self.kwargs))


class MemberFinanceView(DetailView):
    template_name = 'office/member/finance.html'
    context_object_name = 'member'
    model = Member
