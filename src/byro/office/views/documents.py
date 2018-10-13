from django import forms
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from byro.documents.models import Document


class DocumentUploadForm(forms.ModelForm):

    class Meta:
        model = Document
        exclude = ('content_hash', 'member')


class DocumentUploadView(FormView):
    template_name = 'office/documents/add.html'
    model = Document
    form_class = DocumentUploadForm

    @transaction.atomic
    def form_valid(self, form):
        form.save()
        form.instance.log(self, '.saved', file_name=form.instance.document.name, content_size=form.instance.document.size, content_hash=form.instance.content_hash)
        try:
            messages.success(self.request, _('The upload was processed successfully.'))
        except Exception as e:
            messages.error(self.request, _('The upload was added successfully, but could not be processed: ') + str(e))
        self.form = form
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path
