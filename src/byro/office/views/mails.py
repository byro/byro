from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView, UpdateView, View
from i18nfield.forms import I18nModelForm

from byro.mails.models import (
    EMail,
    MailTemplate,
    RecipientsLockedError,
    RecipientType,
)
from byro.mails.send import SendMailException
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
        fields = ["to_type", "to", "reply_to", "cc", "bcc", "subject", "text"]

    # The empty choice matters: without it, a browser preselects the first
    # member whenever no valid member is given, and the mail would go there.
    to_member = forms.ModelChoiceField(
        Member.all_objects.filter(email__isnull=False).exclude(email=""),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(["to_type", "to_member"])

        mail = self.instance
        self._previous_to_type = mail.to_type if mail.pk else None
        self._previous_to = mail.to if mail.pk else None
        recipients = []
        if self._previous_to_type == RecipientType.MEMBER:
            recipients = mail.get_member_recipients()
        # The recipients are shown, but cannot be changed here
        # - after a delivery: the members of the mail are also the record of
        #   who received it, and a retry has to reach the remaining recipients,
        # - with several member recipients, which can only be set in code: the
        #   form selects a single member and would drop the others.
        self.recipients_locked = bool(
            mail.pk and (mail.sent or mail.has_deliveries or len(recipients) > 1)
        )
        self.member_missing = False
        if self.recipients_locked:
            for name in ("to_type", "to", "to_member"):
                self.fields[name].disabled = True
            return

        if recipients:
            self.initial["to_member"] = recipients[0].pk
            # keep the current recipient selectable, even without an address
            self.fields["to_member"].queryset = Member.all_objects.filter(
                Q(pk=recipients[0].pk)
                | Q(pk__in=self.fields["to_member"].queryset.values("pk"))
            )
        if not self.is_bound:
            # A member given by a link or stored in a draft has to be one that
            # can be selected. Otherwise nobody is selected, never another member.
            try:
                member = self.fields["to_member"].to_python(
                    self.initial.get("to_member")
                )
            except forms.ValidationError:
                member = None
            if member is None:
                self.initial["to_member"] = None
                self.member_missing = (
                    self.initial.get("to_type") == RecipientType.MEMBER
                )

    def clean(self):
        cleaned_data = super().clean()
        if self.recipients_locked:
            return cleaned_data
        to_type = cleaned_data.get("to_type")
        if to_type == RecipientType.ADDRESS:
            to = (cleaned_data.get("to") or "").strip()
            if not to:
                self.add_error("to", _("Field cannot be empty"))
            elif to.startswith("special:"):
                self.add_error("to", _("Please enter an email address."))
        elif to_type == RecipientType.MEMBER:
            cleaned_data["to"] = ""
            if not cleaned_data.get("to_member") and "to_member" not in self.errors:
                self.add_error("to_member", _("Please select a member."))
        elif to_type == RecipientType.ALL_MEMBERS:
            cleaned_data["to"] = ""
        return cleaned_data

    def save(self, commit=True):
        # the mail and its member recipient are stored together
        with transaction.atomic():
            return super().save(commit=commit)

    def _save_m2m(self):
        super()._save_m2m()
        if self.recipients_locked:
            return
        to_type = self.cleaned_data["to_type"]
        if to_type == RecipientType.MEMBER:
            self.instance.set_member_recipients([self.cleaned_data["to_member"]])
        elif self._previous_to_type is not None and (
            to_type != self._previous_to_type
            or self.cleaned_data["to"] != self._previous_to
        ):
            # The recipient was selected anew. The members the mail had so far
            # were its recipients, or are left over from an older version;
            # they are no record of a delivery, as nothing was delivered yet
            # (set_member_recipients() refuses to touch a delivered mail).
            self.instance.set_member_recipients([])


class MailSendMixin:
    def form_valid(self, form):
        if form.instance.sent:
            raise forms.ValidationError(
                _(
                    "This mail has been sent already, and cannot be modified. Copy it to a draft instead!"
                )
            )
        try:
            result = super().form_valid(form)
        except RecipientsLockedError:
            # delivered to somebody after the form was opened; nothing was saved
            messages.error(
                self.request,
                _(
                    "This mail has been delivered to some of its recipients in "
                    "the meantime. Its recipients cannot be changed anymore."
                ),
            )
            return redirect(
                reverse("office:mails.mail.view", kwargs={"pk": form.instance.pk})
            )
        if form.data.get("action", "save") == "send":
            try:
                form.instance.send()
            except SendMailException as e:
                messages.error(self.request, str(e))
            else:
                messages.success(
                    self.request,
                    _("Your changes have been saved and the email was sent."),
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

    def get_queryset(self):
        return super().get_queryset().with_member_recipients()


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
        failed = []
        for mail in qs:
            try:
                mail.send()
            except SendMailException as e:
                failed.append(str(e))
        sent = length - len(failed)
        if sent > 1:
            messages.success(
                request, _("{count} mails have been sent.").format(count=sent)
            )
        elif sent == 1:
            messages.success(request, _("The mail has been sent."))
        elif not failed:
            messages.success(request, _("No mail has been sent."))
        if failed:
            messages.error(
                request,
                _("{count} mails could not be sent.").format(count=len(failed)),
            )
            for error in failed:
                messages.error(request, error)
        return redirect(reverse("office:mails.outbox.list"))


class SentMail(ListView):
    queryset = (
        EMail.objects.filter(sent__isnull=False)
        .order_by("-sent")
        .with_member_recipients()
    )
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
