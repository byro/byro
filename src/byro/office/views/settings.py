from django.contrib import messages
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView

from byro.common.forms import ConfigurationForm, RegistrationConfigForm
from byro.common.models import Configuration


class ConfigurationView(FormView):
    form_class = ConfigurationForm
    template_name = 'office/settings/form.html'

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['instance'] = Configuration.get_solo()
        return form_kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('The config was saved successfully.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:settings.base')


class RegistrationConfigView(FormView):
    form_class = RegistrationConfigForm
    template_name = 'office/settings/form.html'

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('The config was saved successfully.'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:settings.registration')
