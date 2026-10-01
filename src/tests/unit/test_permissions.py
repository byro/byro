import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory
from django.views.generic import View

from byro.common.permissions import (
    SuperuserRequiredMixin,
    has_backend_access,
    is_superuser,
    superuser_required,
)


def make_user(is_staff=False, is_superuser=False, is_active=True):
    return User(
        username="someone",
        is_staff=is_staff,
        is_superuser=is_superuser,
        is_active=is_active,
    )


@pytest.mark.parametrize(
    "is_staff,is_superuser_flag,expected",
    (
        (False, False, False),
        (True, False, True),
        (False, True, True),
        (True, True, True),
    ),
)
def test_has_backend_access(is_staff, is_superuser_flag, expected):
    user = make_user(is_staff=is_staff, is_superuser=is_superuser_flag)
    assert has_backend_access(user) is expected


@pytest.mark.parametrize(
    "is_staff,is_superuser_flag,expected",
    (
        (False, False, False),
        (True, False, False),
        (False, True, True),
        (True, True, True),
    ),
)
def test_is_superuser(is_staff, is_superuser_flag, expected):
    user = make_user(is_staff=is_staff, is_superuser=is_superuser_flag)
    assert is_superuser(user) is expected


@pytest.mark.parametrize("check", (has_backend_access, is_superuser))
def test_checks_reject_anonymous_inactive_and_missing_users(check):
    assert check(AnonymousUser()) is False
    assert check(None) is False
    assert check(make_user(is_staff=True, is_superuser=True, is_active=False)) is False


class ProtectedView(SuperuserRequiredMixin, View):
    def get(self, request):
        return HttpResponse("ok")


@superuser_required
def protected_view(request):
    return HttpResponse("ok")


VIEWS = (ProtectedView.as_view(), protected_view)


def request_as(user):
    request = RequestFactory().get("/somewhere/?page=2")
    request.user = user
    return request


@pytest.mark.parametrize("view", VIEWS)
@pytest.mark.parametrize("is_staff", (True, False))
def test_superuser_controls_allow_superusers(view, is_staff):
    request = request_as(make_user(is_staff=is_staff, is_superuser=True))
    response = view(request)
    assert response.status_code == 200
    assert response.content == b"ok"


@pytest.mark.parametrize("view", VIEWS)
@pytest.mark.parametrize(
    "user",
    (
        make_user(is_staff=True),
        make_user(),
        make_user(is_staff=True, is_superuser=True, is_active=False),
    ),
    ids=("staff", "no-flags", "inactive-superuser"),
)
def test_superuser_controls_deny_authenticated_users_with_403(view, user):
    # The controls do not rely on PermissionMiddleware having run before.
    with pytest.raises(PermissionDenied):
        view(request_as(user))


@pytest.mark.parametrize("view", VIEWS)
def test_superuser_controls_send_anonymous_users_to_login(view):
    response = view(request_as(AnonymousUser()))
    assert response.status_code == 302
    assert response.url == "/login/?next=/somewhere/%3Fpage%3D2"


def test_mixin_passes_its_message_to_the_error_page():
    class ExplainedView(SuperuserRequiredMixin, View):
        permission_denied_message = "Ask a superuser."

    with pytest.raises(PermissionDenied) as excinfo:
        ExplainedView.as_view()(request_as(make_user(is_staff=True)))
    assert str(excinfo.value) == "Ask a superuser."
