from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView, View

from byro.common import api_tokens


class ApiTokenView(LoginRequiredMixin, TemplateView):
    template_name = "office/settings/api_token.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["token"] = api_tokens.get_or_create_token(user, actor=user).key
        return context


class ApiTokenRegenerateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        api_tokens.regenerate_token(request.user, actor=request.user)
        return redirect("office:settings.api-token")
