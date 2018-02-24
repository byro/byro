from django.views.generic import DetailView, ListView, View

from byro.mails.models import EMail, MailTemplate


class MailDetail(DetailView):  # TODO
    queryset = EMail.objects.filter(sent__isnull=True)
    template_name = 'office/mails/detail.html'
    context_object_name = 'mail'


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


class SentMail(ListView):  # TODO
    queryset = EMail.objects.filter(sent__isnull=False)
    template_name = 'office/mails/sent.html'
    context_object_name = 'mails'


class TemplateList(ListView):  # TODO
    queryset = MailTemplate.objects.all()


class TemplateDetail(DetailView):  # TODO
    queryset = MailTemplate.objects.all()


class TemplateDelete(View):  # TODO
    pass
