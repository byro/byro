from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, reverse
from django.urls import resolve
from django.utils import translation
from django.utils.translation import gettext as _

from byro.common.models.configuration import Configuration
from byro.common.permissions import has_backend_access, log_out
from byro.common.signals import unauthenticated_urls


class SettingsMiddleware:
    ALLOWED_URLS = (
        "settings.registration",
        "settings.initial",
        "settings.plugins",
        "healthz",
    )
    #: Logging out and switching the account must always be possible. An
    #: account that cannot complete the initial setup itself (no superuser)
    #: would otherwise be stuck on a page it is not allowed to use.
    AUTHENTICATION_VIEWS = frozenset(
        {
            "common:login",
            "common:logout",
            "common:oidc-login",
            "common:oidc-callback",
        }
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        url = resolve(request.path_info)
        translation.activate(settings.DEFAULT_LANGUAGE)
        if (
            not request.user.is_anonymous
            and url.url_name not in self.ALLOWED_URLS
            and url.view_name not in self.AUTHENTICATION_VIEWS
            and url.namespace != "mfa"
        ):
            config = Configuration.get_solo()
            values = ("name", "backoffice_mail", "mail_from")
            if not all(getattr(config, value, None) for value in values):
                return redirect("office:settings.initial")
        return self.get_response(request)


def url_allows_unauthenticated(request, url, sender=None):
    """Return True if the resolved ``url`` may be used without a logged in
    user: core public URLs (login, logout, …) and everything registered via
    the ``unauthenticated_urls`` signal (member pages, REST API, plugins)."""
    if url.url_name in PermissionMiddleware.UNAUTHENTICATED_URLS:
        return True

    unauthenticated_urls_matchers = []
    for _receiver, response in unauthenticated_urls.send(
        sender or PermissionMiddleware
    ):
        unauthenticated_urls_matchers.extend(response)

    for url_matcher in unauthenticated_urls_matchers:
        if callable(url_matcher):
            if url_matcher(request, url):
                return True
        else:
            if url.view_name == url_matcher:
                return True
    return False


class PermissionMiddleware:
    UNAUTHENTICATED_URLS = (
        "login",
        "logout",
        "log.info",
        "oidc-login",
        "oidc-callback",
        "healthz",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        url = resolve(request.path_info)

        if has_backend_access(request.user) or url_allows_unauthenticated(
            request, url, sender=self
        ):
            return self.get_response(request)

        if request.user.is_authenticated:
            # The account lost its backend access (neither staff nor
            # superuser any more) while it was logged in.
            log_out(request)
            messages.error(
                request, _("This account does not have access to the backend.")
            )
            return redirect("common:login")
        return redirect(reverse("common:login") + f"?next={request.path}")
