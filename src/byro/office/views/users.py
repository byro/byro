from django import forms
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, FormView, ListView, UpdateView

from byro.common.models import LogEntry


class UserForm(forms.ModelForm):
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["last_name"].label = _("Name")

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


# FIXME No implemented yet
class UserDeleteView(DetailView):
    model = User
    context_object_name = "user"
