from django import forms
from django.apps import apps
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, TemplateView
from solo.models import SingletonModel

from byro.common.forms import ConfigurationForm, RegistrationConfigForm
from byro.common.models import Configuration


class ConfigurationView(FormView):
    form_class = ConfigurationForm
    template_name = 'office/settings/form.html'

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['instance'] = Configuration.get_solo()
        return form_kwargs

    def get_form(self):
        config_models = [model for model in apps.get_models() if issubclass(model, SingletonModel)]
        data = self.request.POST if self.request.method == 'POST' else None
        return [
            forms.modelform_factory(model, fields='__all__')(prefix=model.__name__, instance=model.get_solo(), data=data)
            for model in config_models
        ]

    def form_valid(self, form):
        for form in self.get_form():
            form.save()
        messages.success(self.request, _('The config was saved successfully.'))
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if all(f.is_valid() for f in form):
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('office:settings.base')


class RegistrationConfigView(FormView):
    form_class = RegistrationConfigForm
    template_name = 'office/settings/registration_form.html'

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('The config was saved successfully.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:settings.registration')

class PluginsView(TemplateView):
    template_name = 'office/settings/plugins.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['plugins'] = []
        for app in apps.get_app_configs():
            if hasattr(app, 'ByroPluginMeta'):
                context['plugins'].append({
                    'meta': app.ByroPluginMeta,
                })
        return context
