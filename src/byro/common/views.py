import urllib

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.http import is_safe_url
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView

from byro.common.models import LogEntry


class LoginView(TemplateView):
    template_name = "common/auth/login.html"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponseRedirect:
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(
                request, _("No user account matches the entered credentials.")
            )
            return redirect("common:login")

        if not user.is_active:
            messages.error(request, _("User account is deactivated."))
            LogEntry.objects.create(
                content_object=user,
                user=user,
                action_type="byro.common.login.deactivated",
            )
            return redirect("common:login")

        login(request, user)
        LogEntry.objects.create(
            content_object=user, user=user, action_type="byro.common.login.success"
        )
        url = urllib.parse.unquote(request.GET.get("next", ""))
        if url and is_safe_url(url, request.get_host()):
            return redirect(url)

        return redirect("/")


def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    if request.user:
        LogEntry.objects.create(
            content_object=request.user,
            user=request.user,
            action_type="byro.common.logout",
        )
    logout(request)
    return redirect("/")


class LogInfoView(TemplateView):
    template_name = "common/log/info.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["log_head"] = LogEntry.objects.get_chain_end()
        context["now"] = now()
        return context
