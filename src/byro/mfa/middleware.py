from django.shortcuts import redirect
from django.urls import resolve

from byro.common.middleware import url_allows_unauthenticated
from byro.mfa import services


class MFAMiddleware:
    """Enforce multi-factor authentication for the office backend.

    Runs after ``AuthenticationMiddleware``, ``OTPMiddleware`` and
    ``PermissionMiddleware``. Authenticated users who need MFA (their own
    device or the global policy) but whose session is not verified yet are
    redirected to the challenge (device present) or to the enrollment (policy
    requires MFA, no device yet). URLs that do not require a login – login,
    logout, member pages, the REST API and everything registered through the
    ``unauthenticated_urls`` signal – are never affected.

    ``request.mfa_locked`` tells templates whether the current user still has
    to pass the MFA step (used to reduce the navigation).
    """

    #: Reachable while authenticated but not (yet) MFA verified.
    EXEMPT_VIEW_NAMES = frozenset(
        {"mfa:challenge", "mfa:challenge.recovery", "common:logout"}
    )
    #: Reachable without verification only for users without a confirmed device.
    ENROLLMENT_VIEW_NAMES = frozenset({"mfa:setup"})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.mfa_locked = False
        if request.user.is_authenticated and services.needs_verification(request):
            request.mfa_locked = True
            url = resolve(request.path_info)
            if self.is_protected(request, url):
                return redirect(
                    services.get_verification_url(
                        request, next_url=request.get_full_path()
                    )
                )
        return self.get_response(request)

    def is_protected(self, request, url):
        if url.view_name in self.EXEMPT_VIEW_NAMES:
            return False
        if url_allows_unauthenticated(request, url):
            return False
        if (
            url.view_name in self.ENROLLMENT_VIEW_NAMES
            and services.get_confirmed_device(request.user) is None
        ):
            return False
        return True
