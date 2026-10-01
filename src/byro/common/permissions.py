"""Central definition of byro's permission model.

``is_staff`` grants access to the office backend and the authenticated API,
``is_superuser`` additionally grants access to administrative functions
(settings, user management, log). A superuser always has backend access, even
without ``is_staff``.

Everything in here checks the user itself and does not rely on
``PermissionMiddleware`` having run, so plugins can use it for their own views.
"""

from functools import wraps

from django.contrib.auth import logout
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from byro.common.models import LogEntry


def has_backend_access(user):
    """Whether ``user`` may use the office backend and the authenticated API."""
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and (user.is_staff or user.is_superuser)
    )


def is_superuser(user):
    """Whether ``user`` may use administrative functions."""
    return bool(user and user.is_authenticated and user.is_active and user.is_superuser)


def log_out(request):
    """End the session of the current user and record it in the audit log."""
    if request.user.is_authenticated:
        LogEntry.objects.create(
            content_object=request.user,
            user=request.user,
            action_type="byro.common.logout",
        )
    logout(request)


def _redirect_to_login(request):
    return redirect_to_login(request.get_full_path(), reverse("common:login"))


class SuperuserRequiredMixin(AccessMixin):
    """Restrict a view to superusers.

    Anonymous users are redirected to the login page, authenticated users
    without superuser status receive ``403 Forbidden``. Set
    ``permission_denied_message`` to explain the restriction on the error
    page.
    """

    def has_permission(self):
        return is_superuser(self.request.user)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied(self.get_permission_denied_message())
        return _redirect_to_login(self.request)

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


def superuser_required(view_func):
    """Function view counterpart of :class:`SuperuserRequiredMixin`."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if is_superuser(request.user):
            return view_func(request, *args, **kwargs)
        if request.user.is_authenticated:
            raise PermissionDenied
        return _redirect_to_login(request)

    return wrapper
