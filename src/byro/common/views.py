import secrets
import urllib

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.views.generic import TemplateView, View

from byro.common.models import LogEntry
from byro.common.oidc import (
    OIDCError,
    build_auth_url,
    exchange_code,
    get_or_create_user,
    is_oidc_configured,
    validate_id_token,
)


class LoginView(TemplateView):
    template_name = "common/auth/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["oidc_enabled"] = is_oidc_configured()
        return ctx

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
        if url and url_has_allowed_host_and_scheme(url, request.get_host()):
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


class OIDCLoginView(View):
    def get(self, request):
        if not is_oidc_configured():
            raise Http404
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        request.session["oidc_state"] = state
        request.session["oidc_nonce"] = nonce
        redirect_uri = request.build_absolute_uri(reverse("common:oidc-callback"))
        try:
            auth_url = build_auth_url(redirect_uri, state, nonce)
        except OIDCError as e:
            messages.error(request, str(e))
            return redirect("common:login")
        return HttpResponseRedirect(auth_url)


class OIDCCallbackView(View):
    def get(self, request):
        if not is_oidc_configured():
            raise Http404

        error = request.GET.get("error")
        if error:
            error_description = request.GET.get("error_description", error)
            messages.error(
                request, _("SSO login failed: %(error)s") % {"error": error_description}
            )
            return redirect("common:login")

        try:
            state = request.GET.get("state", "")
            if not state or not secrets.compare_digest(
                state, request.session.get("oidc_state", "")
            ):
                raise OIDCError("Invalid or missing state parameter")

            code = request.GET.get("code")
            if not code:
                raise OIDCError("Missing authorization code")

            nonce = request.session.pop("oidc_nonce", "")
            request.session.pop("oidc_state", None)
            redirect_uri = request.build_absolute_uri(reverse("common:oidc-callback"))

            token_response = exchange_code(code, redirect_uri)
            id_token = token_response.get("id_token")
            if not id_token:
                raise OIDCError("No id_token in token response")

            claims = validate_id_token(id_token, nonce)
            access_token = token_response.get("access_token", "")
            user = get_or_create_user(claims, access_token)

            if not user.is_active:
                messages.error(request, _("User account is deactivated."))
                return redirect("common:login")

            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)
            LogEntry.objects.create(
                content_object=user,
                user=user,
                action_type="byro.common.login.oidc",
            )
            url = urllib.parse.unquote(request.GET.get("next", ""))
            if url and url_has_allowed_host_and_scheme(url, request.get_host()):
                return redirect(url)
            return redirect("/")

        except OIDCError as e:
            messages.error(request, str(e))
            return redirect("common:login")
