from django.db.models import Q
from django.utils.timezone import now
from django.views.generic import TemplateView

from byro.members.models import Member, Membership
from byro.members.stats import get_member_statistics


class DashboardView(TemplateView):
    template_name = 'office/dashboard.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['member_count'] = Member.objects.all().count()
        context['active_count'] = Membership.objects.filter(Q(start__lte=now().date()) & (Q(end__isnull=True) | Q(end__gte=now().date()))).count()
        context['stats'] = get_member_statistics()
        return context
