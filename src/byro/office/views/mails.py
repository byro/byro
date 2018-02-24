from django import forms
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, ListView, UpdateView, View

from byro.mails.models import EMail, MailTemplate


class MailDetail(UpdateView):
    queryset = EMail.objects.filter(sent__isnull=True)
    template_name = 'office/mails/detail.html'
    context_object_name = 'mail'
    form_class = forms.modelform_factory(EMail, fields=['to', 'reply_to', 'cc', 'bcc', 'subject', 'text'])
    success_url = '/mails/outbox'

    def form_valid(self, form):
        if form.instance.sent:
            raise forms.ValidationError(_('This mail has been sent already, and cannot be modified. Copy it to a draft instead!'))
        messages.success(self.request, _('Your changes have been saved.'))
        return super().form_valid(form)


class MailCopy(View):  # TODO

    def get_object(self):
        return EMail.objects.get(pk=self.kwargs['pk'])


class OutboxList(ListView):
    queryset = EMail.objects.filter(sent__isnull=True)
    template_name = 'office/mails/outbox.html'
    context_object_name = 'mails'


class OutboxPurge(View):  # TODO

    def get_queryset(self):
        qs = EMail.objects.filter(sent__isnull=True, pk=self.kwargs['pk'])
        if 'pk' in self.kwargs:
            return qs.filter(pk=self.kwargs['pk'])
        return qs


class OutboxSend(View):  # TODO

    def get_queryset(self):
        qs = EMail.objects.filter(sent__isnull=True, pk=self.kwargs['pk'])
        if 'pk' in self.kwargs:
            return qs.filter(pk=self.kwargs['pk'])
        return qs


class SentMail(ListView):
    queryset = EMail.objects.filter(sent__isnull=False)
    template_name = 'office/mails/sent.html'
    context_object_name = 'mails'


class TemplateList(ListView):
    queryset = MailTemplate.objects.all()
    template_name = 'office/mails/templates.html'
    context_object_name = 'templates'


class TemplateDetail(DetailView):  # TODO
    queryset = MailTemplate.objects.all()


class TemplateDelete(View):  # TODO
    pass
