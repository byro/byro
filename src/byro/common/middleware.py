from django.shortcuts import redirect, reverse
from django.urls import resolve

from byro.common.models.configuration import Configuration
from byro.common.signals import unauthenticated_urls


class SettingsMiddleware:
    ALLOWED_URLS = ("settings.registration", "settings.initial", "settings.plugins")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        url = resolve(request.path_info)
        if not request.user.is_anonymous and url.url_name not in self.ALLOWED_URLS:
            config = Configuration.get_solo()
            values = ("name", "backoffice_mail", "mail_from")
            if not all(getattr(config, value, None) for value in values):
                return redirect("office:settings.initial")
        return self.get_response(request)


class PermissionMiddleware:
    UNAUTHENTICATED_URLS = ("login", "logout", "log.info")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        url = resolve(request.path_info)

        allow = True

        if request.user.is_anonymous and url.url_name not in self.UNAUTHENTICATED_URLS:
            allow = False

        if not allow:
            unauthenticated_urls_matchers = []
            for receiver, response in unauthenticated_urls.send(self):
                unauthenticated_urls_matchers.extend(response)

            for url_matcher in unauthenticated_urls_matchers:
                if callable(url_matcher):
                    if url_matcher(request, url):
                        allow = True
                        break
                else:
                    if url.view_name == url_matcher:
                        allow = True
                        break

        if not allow:
            return redirect(
                reverse("common:login") + "?next={request.path}".format(request=request)
            )
        else:
            return self.get_response(request)
