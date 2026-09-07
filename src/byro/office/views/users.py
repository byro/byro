from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, UpdateView, View
from rest_framework.authtoken.models import Token

from byro.common.models import LogEntry


class UserForm(forms.ModelForm):
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["last_name"].label = _("Name")
        # Only superusers may grant or revoke staff/superuser rights. This
        # also stops a staff-only user from escalating their own account
        # (or anyone else's) to superuser by tampering with the submitted
        # form, since a field removed here is dropped from cleaned_data too.
        if request_user is None or not request_user.is_superuser:
            del self.fields["is_superuser"]
            del self.fields["is_staff"]

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


class UserListView(ListView):
    template_name = "office/user/list.html"
    context_object_name = "users"
    model = User
    paginate_by = 25


class UserCreateView(FormView):
    template_name = "office/user/add.html"
    model = User
    form_class = UserForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, _("Only superusers may add new users."))
            return redirect(reverse("office:settings.users.list"))
        return super().dispatch(request, *args, **kwargs)

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
    template_name = "office/user/detail.html"
    context_object_name = "user"
    model = User
    form_class = UserForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.pk != kwargs["pk"] and not request.user.is_superuser:
            messages.error(request, _("Only superusers may edit other users."))
            return redirect(
                reverse("office:settings.users.detail", kwargs={"pk": request.user.pk})
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        LogEntry.objects.create(
            content_object=form.instance,
            user=self.request.user,
            action_type="byro.common.user.updated",
        )
        return super().form_valid(form)

    def get_object(self):
        return User.objects.get(pk=self.kwargs["pk"])

    def get_success_url(self):
        return reverse("office:settings.users.detail", kwargs={"pk": self.kwargs["pk"]})


class UserPasswordDisableView(View):
    def post(self, request, pk, *args, **kwargs):
        if request.user.pk == pk:
            messages.error(request, _("You cannot disable your own password."))
            return redirect(reverse("office:settings.users.detail", kwargs={"pk": pk}))
        if not request.user.is_superuser:
            messages.error(
                request, _("Only superusers may disable another user's password.")
            )
            return redirect(
                reverse("office:settings.users.detail", kwargs={"pk": request.user.pk})
            )
        user = get_object_or_404(User, pk=pk)
        user.set_unusable_password()
        user.save()
        # A disabled password must not leave a still-valid API token behind,
        # or the account could still authenticate against the API.
        Token.objects.filter(user=user).delete()
        LogEntry.objects.create(
            content_object=user,
            user=request.user,
            action_type="byro.common.user.password_disabled",
        )
        messages.success(
            request,
            _("The user's password has been disabled and their API token revoked."),
        )
        return redirect(reverse("office:settings.users.detail", kwargs={"pk": pk}))


class UserApiTokenRegenerateView(View):
    def post(self, request, pk, *args, **kwargs):
        if request.user.pk != pk and not request.user.is_superuser:
            messages.error(
                request, _("Only superusers may regenerate another user's API token.")
            )
            return redirect(
                reverse("office:settings.users.detail", kwargs={"pk": request.user.pk})
            )
        user = get_object_or_404(User, pk=pk)
        Token.objects.filter(user=user).delete()
        Token.objects.create(user=user)
        LogEntry.objects.create(
            content_object=user,
            user=request.user,
            action_type="byro.common.user.token_regenerated",
        )
        messages.success(request, _("The user's API token has been regenerated."))
        return redirect(reverse("office:settings.users.detail", kwargs={"pk": pk}))


# FIXME No implemented yet
class UserDeleteView(DetailView):
    model = User
    context_object_name = "user"
