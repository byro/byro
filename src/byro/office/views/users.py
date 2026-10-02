from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, UpdateView, View

from byro.common import api_tokens
from byro.common.models import LogEntry
from byro.common.permissions import (
    SuperuserRequiredMixin,
    has_backend_access,
    is_superuser,
)


class UserForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Password"),
        # Keeps browsers from filling in the saved password of the editor.
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, request_user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["last_name"].label = _("Name")
        if self.instance.pk:
            # Existing accounts keep their password unless a new one is entered.
            self.fields["password"].required = False
            self.fields["password"].help_text = _(
                "Leave empty to leave the password unchanged."
            )
        if not is_superuser(request_user):
            # Only superusers manage permissions. Removing the fields also
            # drops any submitted value, so nobody can promote themselves.
            del self.fields["is_staff"]
            del self.fields["is_superuser"]
            return

        self.fields["is_staff"].label = _("Backend access (staff)")
        self.fields["is_staff"].help_text = _(
            "Allows this account to log in to the backend and to use the API."
        )
        self.fields["is_superuser"].label = _("Superuser")
        self.fields["is_superuser"].help_text = _(
            "Additionally grants access to the settings, the user management "
            "and the log. Superusers can always log in, even without backend "
            "access."
        )
        if not self.instance.pk:
            # New accounts get backend access unless it is switched off.
            self.initial["is_staff"] = True
        elif self.instance.pk == request_user.pk:
            # A disabled field ignores submitted data, so superusers cannot
            # remove their own status and at least one superuser remains.
            self.fields["is_superuser"].disabled = True
            self.fields["is_superuser"].help_text = _(
                "You cannot change your own superuser status."
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        password = self.cleaned_data.get("password")
        if password:
            self.instance.set_password(password)
            self.instance.save()

    class Meta:
        model = User
        fields = [
            "username",
            "last_name",
            "email",
            "is_superuser",
            "is_staff",
        ]


class UserListView(SuperuserRequiredMixin, ListView):
    template_name = "office/user/list.html"
    context_object_name = "users"
    model = User
    paginate_by = 25


class UserCreateView(SuperuserRequiredMixin, FormView):
    template_name = "office/user/add.html"
    model = User
    form_class = UserForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        self.form = form
        LogEntry.objects.create(
            content_object=form.instance,
            user=self.request.user,
            action_type="byro.common.user.created",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "office:settings.users.detail", kwargs={"pk": self.form.instance.pk}
        )


class UserDetailView(UpdateView):
    """Every backend user may edit their own profile, other accounts are
    managed by superusers only."""

    template_name = "office/user/detail.html"
    context_object_name = "user"
    model = User
    form_class = UserForm

    def dispatch(self, request, *args, **kwargs):
        # Checked before the account is looked up, so the answer does not
        # reveal whether an account with this id exists.
        user = request.user
        own_profile = has_backend_access(user) and kwargs["pk"] == user.pk
        if not own_profile and not is_superuser(user):
            raise PermissionDenied(_("Only superusers may manage other user accounts."))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Only whether a token exists: the token itself is never part of the
        # user management.
        context["has_api_token"] = api_tokens.has_token(self.object)
        return context

    def form_valid(self, form):
        LogEntry.objects.create(
            content_object=form.instance,
            user=self.request.user,
            action_type="byro.common.user.updated",
        )
        return super().form_valid(form)

    def get_object(self):
        return get_object_or_404(User, pk=self.kwargs["pk"])

    def get_success_url(self):
        return reverse("office:settings.users.detail", kwargs={"pk": self.kwargs["pk"]})


class UserPasswordDisableView(SuperuserRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        if request.user.pk == pk:
            messages.error(request, _("You cannot disable your own password."))
            return redirect(reverse("office:settings.users.detail", kwargs={"pk": pk}))
        user = get_object_or_404(User, pk=pk)
        user.set_unusable_password()
        user.save()
        LogEntry.objects.create(
            content_object=user,
            user=request.user,
            action_type="byro.common.user.password_disabled",
        )
        messages.success(request, _("The user's password has been disabled."))
        return redirect(reverse("office:settings.users.detail", kwargs={"pk": pk}))


@method_decorator(transaction.non_atomic_requests, name="dispatch")
class UserApiTokenRevokeView(SuperuserRequiredMixin, View):
    """Invalidate the API token of another account. The token itself is never
    shown or replaced here: the account owner gets a new one on their own API
    token page.

    The revocation commits on its own and refuses to run inside another
    transaction, so this view stays outside of ``ATOMIC_REQUESTS``."""

    def post(self, request, pk, *args, **kwargs):
        if request.user.pk == pk:
            messages.error(
                request, _("Use your own API token page to manage your token.")
            )
            return redirect("office:settings.api-token")
        user = get_object_or_404(User, pk=pk)
        try:
            result = api_tokens.revoke_token(user, actor=request.user)
        except api_tokens.ApiTokenAccountMissing as exc:
            # removed between the lookup and the row lock
            raise Http404 from exc
        # Any other failure is an error page: the revocation has no confirmed
        # result, and the page of the account shows the state of its token.
        if not result.revoked:
            messages.info(request, _("This user has no API token."))
        elif result.audited:
            messages.success(
                request,
                _(
                    "The API token has been revoked and no longer works. The "
                    "user can obtain a new token from their API token page."
                ),
            )
        else:
            messages.warning(
                request,
                _(
                    "The API token has been revoked and no longer works, but the "
                    "audit log entry could not be written. Please inform whoever "
                    "operates this installation. The user can obtain a new token "
                    "from their API token page."
                ),
            )
        return redirect(reverse("office:settings.users.detail", kwargs={"pk": pk}))


# FIXME No implemented yet
class UserDeleteView(DetailView):
    model = User
    context_object_name = "user"
