from django.views.generic import TemplateView, ListView, DetailView

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
