from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, ListView, UpdateView, View
from i18nfield.forms import I18nModelForm

from byro.mails.models import EMail, MailTemplate
from byro.members.models import Member


class RestrictedLanguagesI18nModelForm(I18nModelForm):
    def __init__(self, *args, **kwargs):
        if "locales" not in kwargs:
            from byro.common.models import Configuration

            config = Configuration.get_solo()
            kwargs["locales"] = [config.language or settings.LANGUAGE_CODE]
        return super().__init__(*args, **kwargs)


class MailSpecialToFormClass(forms.ModelForm):
    class Meta:
        model = EMail
        form = RestrictedLanguagesI18nModelForm
        fields = ["to", "reply_to", "cc", "bcc", "subject", "text"]

    to_type = forms.ChoiceField(
        choices=[
            ("addr", _("Specific address")),
            ("member", _("Member")),
            ("all", _("All members")),
        ],
        widget=forms.RadioSelect,
        initial="addr",
    )

    to_member = forms.ModelChoiceField(
        Member.objects.filter(email__isnull=False).exclude(email=""),
        required=False,
        empty_label=None,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._decode_special(self.initial)
        self.fields[
            "to"
        ].required = (
            False  # FIXME Needs to be re-added in case no special mode is active
        )
        self.order_fields(["to_type", "to_member"])

    @staticmethod
    def _decode_special(d):
        if not d:
            return
        if "to" in d:
            to = d["to"]
            d["to_type"] = "addr"
            if to.startswith("special:"):
                if to.startswith("special:all"):
                    d["to_type"] = "all"
                    del d["to"]
                elif to.startswith("special:member:"):
                    d["to_type"] = "member"
                    d["to_member"] = Member.objects.get(pk=to.split(":", 2)[2])
                    del d["to"]

    def _encode_special(self):
        if self.cleaned_data["to_type"] == "all":
            self.cleaned_data["to"] = "special:all"
        elif self.cleaned_data["to_type"] == "member":
            self.cleaned_data["to"] = "special:member:{}".format(
                self.cleaned_data["to_member"].pk
            )
        self.initial["to_type"] = None
        self.initial["to_member"] = None
        del self.cleaned_data["to_type"]
        del self.cleaned_data["to_member"]
        self.instance.to = self.cleaned_data["to"]
        if not self.cleaned_data["to"]:
            self.add_error("to", _("Field cannot be empty"))
            self.initial["to_type"] = "addr"

    def clean(self):
        self._encode_special()
        return super().clean()


class MailSendMixin:
    def form_valid(self, form):
        if form.instance.sent:
            raise forms.ValidationError(
                _(
                    "This mail has been sent already, and cannot be modified. Copy it to a draft instead!"
                )
            )
        result = super().form_valid(form)
        if form.data.get("action", "save") == "send":
            form.instance.send()
            messages.success(
                self.request, _("Your changes have been saved and the email was sent.")
            )
        else:
            messages.success(self.request, _("Your changes have been saved."))
        return result


class MailDetail(MailSendMixin, UpdateView):
    queryset = EMail.objects.all()
    template_name = "office/mails/detail.html"
    context_object_name = "mail"
    form_class = MailSpecialToFormClass
    success_url = "/mails/outbox"

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        if form.instance.sent:
            for field in form.fields.values():
                field.disabled = True
        return form


class MailCopy(View):
    def get_object(self):
        return EMail.objects.get(pk=self.kwargs["pk"])

    def dispatch(self, request, *args, **kwargs):
        new_mail = self.get_object().copy_to_draft()
        messages.success(request, _("Here is your new mail draft!"))
        return redirect(reverse("office:mails.mail.view", kwargs={"pk": new_mail.pk}))


class OutboxQueryset:
    def get_queryset(self):
        qs = EMail.objects.filter(sent__isnull=True)
        if "pk" in self.kwargs:
            return qs.filter(pk=self.kwargs["pk"])
        return qs


class OutboxList(OutboxQueryset, ListView):
    template_name = "office/mails/outbox.html"
    context_object_name = "mails"


class OutboxPurge(OutboxQueryset, View):
    def dispatch(self, request, *args, **kwargs):
        qs = self.get_queryset()
        length = len(qs)
        qs.delete()
        if length > 1:
            message = _("{count} mails have been deleted.").format(count=length)
        elif length == 1:
            message = "The mail has been deleted."
        else:
            message = "No mail has been deleted."
        messages.success(request, message)
        return redirect(reverse("office:mails.outbox.list"))


class OutboxSend(OutboxQueryset, View):
    def dispatch(self, request, *args, **kwargs):
        qs = self.get_queryset()
        length = len(qs)
        for mail in qs:
            mail.send()
        if length > 1:
            message = _("{count} mails have been sent.").format(count=length)
        elif length == 1:
            message = _("The mail has been sent.")
        else:
            message = _("No mail has been sent.")
        messages.success(request, message)
        return redirect(reverse("office:mails.outbox.list"))


class SentMail(ListView):
    queryset = EMail.objects.filter(sent__isnull=False).order_by("-sent")
    template_name = "office/mails/sent.html"
    context_object_name = "mails"


class TemplateList(ListView):
    queryset = MailTemplate.objects.all()
    template_name = "office/mails/templates.html"
    context_object_name = "templates"


MAIL_TEMPLATE_FORM_CLASS = forms.modelform_factory(
    MailTemplate,
    form=RestrictedLanguagesI18nModelForm,
    fields=["subject", "text", "reply_to", "bcc"],
)


class TemplateDetail(UpdateView):
    queryset = MailTemplate.objects.all()
    template_name = "office/mails/template_detail.html"
    context_object_name = "template"
    success_url = "/mails/templates"
    form_class = MAIL_TEMPLATE_FORM_CLASS


class TemplateCreate(CreateView):
    model = MailTemplate
    template_name = "office/mails/template_detail.html"
    context_object_name = "template"
    success_url = "/mails/templates"
    form_class = MAIL_TEMPLATE_FORM_CLASS


class Compose(SuccessMessageMixin, MailSendMixin, CreateView):
    model = MailTemplate
    template_name = "office/mails/compose.html"
    context_object_name = "template"
    success_url = "/mails/outbox"
    form_class = MailSpecialToFormClass

    def get_initial(self):
        return {k: v for (k, v) in self.request.GET.items()}


class TemplateDelete(View):  # TODO
    pass
