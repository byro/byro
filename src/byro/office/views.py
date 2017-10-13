from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView, TemplateView

from byro.common.forms import ConfigurationForm
from byro.common.models import Configuration
from byro.members.models import Member


class DashboardView(TemplateView):
    template_name = 'office/dashboard.html'


class MemberListView(ListView):
    template_name = 'office/member_list.html'
    context_object_name = 'members'
    model = Member


class MemberDetailView(DetailView):
    template_name = 'office/member_detail.html'
    context_object_name = 'member'
    model = Member


class ConfigurationView(FormView):
    form_class = ConfigurationForm
    template_name = 'office/settings/form.html'

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['instance'] = Configuration.get_solo()
        return form_kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:settings')
