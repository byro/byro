from rest_framework.permissions import BasePermission

from byro.common.permissions import has_backend_access


class HasBackendAccess(BasePermission):
    """Allow the same accounts that may use the office backend: active staff
    users and superusers (DRF's ``IsAdminUser`` only accepts ``is_staff``)."""

    def has_permission(self, request, view):
        return has_backend_access(request.user)
