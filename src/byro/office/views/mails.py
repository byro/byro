from django import forms
from django.contrib import messages
from django.shortcuts import redirect, reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, ListView, UpdateView, View

from byro.mails.models import EMail, MailTemplate


class MailDetail(UpdateView):
    queryset = EMail.objects.all()
    template_name = 'office/mails/detail.html'
    context_object_name = 'mail'
    form_class = forms.modelform_factory(EMail, fields=['to', 'reply_to', 'cc', 'bcc', 'subject', 'text'])
    success_url = '/mails/outbox'

    def form_valid(self, form):
        if form.instance.sent:
            raise forms.ValidationError(_('This mail has been sent already, and cannot be modified. Copy it to a draft instead!'))
        messages.success(self.request, _('Your changes have been saved.'))
        return super().form_valid(form)

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        if form.instance.sent:
            for field in form.fields.values():
                field.disabled = True
        return form


class MailCopy(View):

    def get_object(self):
        return EMail.objects.get(pk=self.kwargs['pk'])

    def dispatch(self, request, *args, **kwargs):
        new_mail = self.get_object().copy_to_draft()
        messages.success(request, _('Here is your new mail draft!'))
        return redirect(reverse('office:mails.mail.view', kwargs={'pk': new_mail.pk}))


class OutboxList(ListView):
    queryset = EMail.objects.filter(sent__isnull=True)
    template_name = 'office/mails/outbox.html'
    context_object_name = 'mails'


class OutboxPurge(View):

    def get_queryset(self):
        qs = EMail.objects.filter(sent__isnull=True)
        if 'pk' in self.kwargs:
            return qs.filter(pk=self.kwargs['pk'])
        return qs

    def dispatch(self, request, *args, **kwargs):
        qs = self.get_queryset()
        length = len(qs)
        qs.delete()
        if length > 1:
            message = _('{count} mails have been deleted.').format(count=length)
        elif length == 1:
            message = 'The mail has been deleted.'
        else:
            message = 'No mail has been deleted.'
        messages.success(request, message)
        return redirect(reverse('office:mails.outbox.list'))


class OutboxSend(View):

    def get_queryset(self):
        qs = EMail.objects.filter(sent__isnull=True)
        if 'pk' in self.kwargs:
            return qs.filter(pk=self.kwargs['pk'])
        return qs

    def dispatch(self, request, *args, **kwargs):
        qs = self.get_queryset()
        length = len(qs)
        for mail in qs:
            mail.send()
        if length > 1:
            message = _('{count} mails have been sent.').format(count=length)
        elif length == 1:
            message = _('The mail has been sent.')
        else:
            message = _('No mail has been sent.')
        messages.success(request, message)
        return redirect(reverse('office:mails.outbox.list'))


class SentMail(ListView):
    queryset = EMail.objects.filter(sent__isnull=False).order_by('-sent')
    template_name = 'office/mails/sent.html'
    context_object_name = 'mails'


class TemplateList(ListView):
    queryset = MailTemplate.objects.all()
    template_name = 'office/mails/templates.html'
    context_object_name = 'templates'


class TemplateDetail(UpdateView):
    queryset = MailTemplate.objects.all()
    template_name = 'office/mails/template_detail.html'
    context_object_name = 'template'
    fields = ['subject', 'text', 'reply_to', 'bcc']
    success_url = '/mails/templates'


class TemplateCreate(CreateView):
    model = MailTemplate
    template_name = 'office/mails/template_detail.html'
    context_object_name = 'template'
    fields = ['subject', 'text', 'reply_to', 'bcc']
    success_url = '/mails/templates'


class TemplateDelete(View):  # TODO
    pass
