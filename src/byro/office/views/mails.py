from django.views.generic import DetailView, ListView, View

from byro.mails.models import EMail, MailTemplate


class MailDetail(DetailView):
    queryset = EMail.objects.filter(sent__isnull=True)


class MailCopy(View):

    def get_object(self):
        return EMail.objects.get(pk=self.kwargs['pk'])


class OutboxList(ListView):
    queryset = EMail.objects.filter(sent__isnull=True)
    template_name = 'office/mails/outbox.html'
    context_object_name = 'mails'


class OutboxPurge(View):

    def get_queryset(self):
        qs = EMail.objects.filter(sent__isnull=True, pk=self.kwargs['pk'])
        if 'pk' in self.kwargs:
            return qs.filter(pk=self.kwargs['pk'])
        return qs


class OutboxSend(View):

    def get_queryset(self):
        qs = EMail.objects.filter(sent__isnull=True, pk=self.kwargs['pk'])
        if 'pk' in self.kwargs:
            return qs.filter(pk=self.kwargs['pk'])
        return qs


class SentMail(ListView):
    queryset = EMail.objects.filter(sent__isnull=False)


class TemplateList(ListView):
    queryset = MailTemplate.objects.all()


class TemplateDetail(DetailView):
    queryset = MailTemplate.objects.all()


class TemplateDelete(View):
    pass
