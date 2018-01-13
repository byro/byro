from django import forms
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, ListView

from byro.bookkeeping.models import RealTransactionSource


class UploadForm(forms.ModelForm):

    class Meta:
        model = RealTransactionSource
        fields = ('source_file', )


class UploadListView(ListView):
    template_name = 'office/upload/list.html'
    context_object_name = 'uploads'
    model = RealTransactionSource


class CsvUploadView(FormView):
    template_name = 'office/upload/add.html'
    model = RealTransactionSource
    form_class = UploadForm

    def form_valid(self, form):
        form.save()
        try:
            form.instance.process()
            messages.success(self.request, _('The upload was processed successfully.'))
        except Exception as e:
            messages.error(self.request, _('The upload was added successfully, but could not be processed: ') + str(e))
        self.form = form
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path
