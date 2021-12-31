import os

from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import FileResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView

from byro.documents.models import Document, get_document_category_names


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        exclude = ("content_hash", "member")

    def __init__(self, *args, **kwargs):
        initial_category = kwargs.pop("initial_category", "byro.documents.misc")

        super().__init__(*args, **kwargs)

        categories = get_document_category_names()

        self.fields["category"] = forms.ChoiceField(
            choices=sorted(categories.items()), initial=initial_category
        )
        if "class" in self.fields["date"].widget.attrs:
            self.fields["date"].widget.attrs["class"] += " datepicker"
        else:
            self.fields["date"].widget.attrs["class"] = "datepicker"


class DocumentUploadView(FormView):
    template_name = "office/documents/add.html"
    model = Document
    form_class = DocumentUploadForm

    @transaction.atomic
    def form_valid(self, form):
        form.save()
        form.instance.log(
            self,
            ".saved",
            file_name=form.instance.document.name,
            content_size=form.instance.document.size,
            content_hash=form.instance.content_hash,
        )
        try:
            messages.success(self.request, _("The upload was processed successfully."))
        except Exception as e:
            messages.error(
                self.request,
                _("The upload was added successfully, but could not be processed: ")
                + str(e),
            )
        self.form = form
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path


class DocumentDetailView(DetailView):
    template_name = "office/documents/detail.html"
    model = Document
    context_object_name = "document"


class DocumentDownloadView(DetailView):
    model = Document
    context_object_name = "document"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # HACK HACK
        # FileResponse can work with a file stream, and do optimized sending with some WSGI servers
        # but the FieldFile in a FileField will be closed upon return from this function, while
        # the wsgi.file_wrapper will operate after returning from Django.
        # dup() the open file, then return an fdopen()
        # FIXME: Fallback to another mechanism for non-local media storage
        response_file = os.fdopen(os.dup(self.object.document.fileno()), mode="rb")
        response = FileResponse(
            response_file,
            content_type=self.object.mime_type_guessed,
            filename=self.object.basename,
        )
        # The actions above may have seeked the fd
        response_file.seek(0)
        return response
