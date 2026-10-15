from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, View

from byro.documents.models import Document, get_document_category_names, guess_mime_type


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
            file_name=form.instance.filename,
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
        return reverse("office:documents.add")


class DocumentDetailView(DetailView):
    template_name = "office/documents/detail.html"
    model = Document
    context_object_name = "document"


class DocumentDownloadView(DetailView):
    model = Document
    context_object_name = "document"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            # FileResponse closes the handle when it is done
            response_file = self.object.open_file()
        except FileNotFoundError:
            raise Http404
        # Detect the type from the handle that is sent, so that the file is
        # opened only once. Only the types in INLINE_MIME_TYPES are shown in
        # the browser, anything else is downloaded as opaque data.
        self.object.mime_type_guessed = guess_mime_type(
            next(response_file.chunks(), b"")
        )
        response_file.seek(0)
        inline_mime_type = self.object.inline_mime_type
        response = FileResponse(
            response_file,
            content_type=inline_mime_type or "application/octet-stream",
            as_attachment=inline_mime_type is None,
            filename=self.object.download_filename,
        )
        if inline_mime_type:
            # The detail page shows the document in a frame. Everything else
            # keeps the DENY of XFrameOptionsMiddleware.
            response["X-Frame-Options"] = "SAMEORIGIN"
        return response


class DocumentLegacyDownloadView(View):
    """The download URL used to end with the file name, which identified
    nothing. Old links lead to the current URL."""

    def get(self, request, pk, filename):
        return redirect("office:documents.download", pk=pk)
