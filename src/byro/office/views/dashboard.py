from django.views.generic import TemplateView

from byro.members.models import Member, Membership


class DashboardView(TemplateView):
    template_name = 'office/dashboard.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['member_count'] = Member.objects.all().count()
        context['active_count'] = Membership.objects.filter(end__isnull=True).count()
        return context
