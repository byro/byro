from django import forms
from django.apps import apps
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, TemplateView, ListView

from byro.bookkeeping.models import Account
from byro.common.forms import ConfigurationForm, RegistrationConfigForm, InitialForm
from byro.common.models import LogEntry
from byro.common.models.configuration import Configuration, ByroConfiguration


class InitialSettings(FormView):
    form_class = InitialForm
    template_name = "office/settings/initial.html"

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["instance"] = Configuration.get_solo()
        return form_kwargs

    @transaction.atomic
    def form_valid(self, form):
        form.save()
        other_data = {
            "accounts": [
                {"account": acc, "name": acc.name, "balances": acc.balances()}
                for acc in Account.objects.all()
            ]
        }
        form.instance.log(
            self, ".initial", initial_data=form.cleaned_data, other_data=other_data
        )
        messages.success(
            self.request,
            _(
                "You're nearly ready to go – configure how you want to add new members, and you're done."
            ),
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("office:settings.registration")


class ConfigurationView(FormView):
    form_class = ConfigurationForm
    template_name = "office/settings/form.html"

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["instance"] = Configuration.get_solo()
        return form_kwargs

    def get_form(self):
        config_models = [
            model for model in apps.get_models() if issubclass(model, ByroConfiguration)
        ]
        data = self.request.POST if self.request.method == "POST" else None
        return [
            forms.modelform_factory(
                model, fields="__all__", exclude=("registration_form",)
            )(prefix=model.__name__, instance=model.get_solo(), data=data)
            for model in config_models
        ]

    @transaction.atomic
    def form_valid(self, form):
        for f in form:
            f.save()
            if f.changed_data:
                f.instance.log(
                    self,
                    "byro.settings.changed",
                    changes={
                        k: (self._original_values[f][k], f.cleaned_data[k])
                        for k in f.changed_data
                    },
                )

        messages.success(self.request, _("The config was saved successfully."))
        return super().form_valid(f)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self._original_values = {
            f: {k: getattr(f.instance, k) for k in f.fields} for f in form
        }
        if all(f.is_valid() for f in form):
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("office:settings.base")


class RegistrationConfigView(FormView):
    form_class = RegistrationConfigForm
    template_name = "office/settings/registration_form.html"

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("The config was saved successfully."))
        LogEntry.objects.create(
            content_object=Configuration.get_solo(),
            user=self.request.user,
            action_type="byro.settings.registration.changed",
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("office:settings.registration")


class AboutByroView(TemplateView):
    template_name = "office/settings/about.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["plugins"] = []
        for app in apps.get_app_configs():
            if hasattr(app, "ByroPluginMeta") and hasattr(app.ByroPluginMeta, "name"):
                context["plugins"].append({"meta": app.ByroPluginMeta})
        return context


class LogView(ListView):
    template_name = "office/settings/log.html"
    context_object_name = "log_entries"
    model = LogEntry
    paginate_by = 50
