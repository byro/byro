from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView, View
from rest_framework.authtoken.models import Token


class ApiTokenView(LoginRequiredMixin, TemplateView):
    template_name = "office/settings/api_token.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token, _ = Token.objects.get_or_create(user=self.request.user)
        context["token"] = token.key
        return context


class ApiTokenRegenerateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Token.objects.filter(user=request.user).delete()
        Token.objects.create(user=request.user)
        return redirect("office:settings.api-token")
