from django.views.generic import DetailView, FormView, ListView

from byro.members.models import Member
from byro.members.forms import CreateMemberForm


class MemberListView(ListView):
    template_name = 'office/member_list.html'
    context_object_name = 'members'
    model = Member


class MemberDetailView(DetailView):
    template_name = 'office/member_detail.html'
    context_object_name = 'member'
    model = Member


class MemberCreateView(FormView):
    template_name = 'office/settings/form.html'
    form_class = CreateMemberForm

    def get_object(self):
        return Member.objects.get(pk=self.kwargs['pk'])

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:member.detail', kwargs=self.kwargs)
