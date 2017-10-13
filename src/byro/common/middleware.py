from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, reverse
from django.urls import resolve


class PermissionMiddleware:
    UNAUTHENTICATED_URLS = (
        'login',
        'logout',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        url = resolve(request.path_info)
        if request.user.is_anonymous and url.url_name not in self.UNAUTHENTICATED_URLS:
            return redirect(reverse('common:login') + f'?next={request.path}')
        return self.get_response(request)
