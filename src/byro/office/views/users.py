from django import forms
from django.contrib.auth.models import User
from django.urls import reverse
from django.views.generic import DetailView, FormView, ListView, UpdateView


class UserListView(ListView):
    template_name = 'office/user/list.html'
    context_object_name = 'users'
    model = User
    paginate_by = 25


class UserCreateView(FormView):
    template_name = 'office/user/add.html'
    model = User
    form_class = forms.modelform_factory(User, fields=['username', 'password', 'last_name', 'email', 'is_superuser', 'is_staff', 'is_active'])

    def form_valid(self, form):
        form.save()
        self.form = form
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:users.detail', kwargs={'pk': self.form.instance.pk})


class UserDetailView(UpdateView):
    template_name = 'office/user/detail.html'
    context_object_name = 'user'
    model = User
    form_class = forms.modelform_factory(User, fields=['last_name', 'email', 'is_superuser', 'is_staff', 'is_active'])

    def get_object(self):
        return User.objects.get(pk=self.kwargs['pk'])

    def get_success_url(self):
        return reverse('office:users.detail', kwargs={'pk': self.object.pk})


# FIXME No implemented yet
class UserDeleteView(DetailView):
    model = User
    context_object_name = 'user'
