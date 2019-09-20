from django.views.generic import TemplateView

from byro.members.models import Member
from byro.members.stats import get_member_statistics


class DashboardView(TemplateView):
    template_name = "office/dashboard.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["member_count"] = Member.objects.all().count()
        context["active_count"] = Member.objects.with_active_membership().count()
        context["stats"] = get_member_statistics()
        return context
