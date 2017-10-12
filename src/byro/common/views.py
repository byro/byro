import random
import urllib

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import is_safe_url
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView


class LoginView(TemplateView):
    template_name = 'common/auth/login.html'

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponseRedirect:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request, _('No user account matches the entered credentials.'))
            return redirect('common:login')

        if not user.is_active:
            messages.error(request, _('User account is deactivated.'))
            return redirect('common:login')

        login(request, user)
        url = urllib.parse.unquote(request.GET.get('next', ''))
        if url and is_safe_url(url, request.get_host()):
            return redirect(url)

        return redirect('/')


def logout_view(request: HttpRequest) -> HttpResponseRedirect:
    logout(request)
    return redirect('/')
