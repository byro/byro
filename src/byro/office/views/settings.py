from django.urls import reverse
from django.views.generic import FormView

from byro.common.forms import ConfigurationForm
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
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('office:settings')
