from rest_framework.permissions import BasePermission


class IsStaffOrSuperuser(BasePermission):
    """Allows access to any active user who is staff or a superuser.

    Mirrors the office login gate (see ``LoginView``/``OIDCCallbackView``):
    an account needs neither, either, or both flags to log in, so the API
    should not be stricter than the web login by requiring ``is_staff``
    alone (DRF's built-in ``IsAdminUser`` does exactly that).
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and (user.is_staff or user.is_superuser))
