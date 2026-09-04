import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, FormView, ListView

from byro.bookkeeping.bank_import import (
    BankTransactionImportError,
    get_bank_transaction_importers,
)
from byro.bookkeeping.models import RealTransactionSource
from byro.bookkeeping.signals import process_csv_upload

logger = logging.getLogger(__name__)

#: Pseudo importer choice that routes the upload through the legacy
#: ``process_csv_upload`` signal. Not a registered importer; sources created
#: with it keep ``importer=None``.
LEGACY_IMPORTER_CHOICE = "byro.bookkeeping.legacy_csv_upload"

DEFAULT_MAX_IMPORT_FILE_SIZE = 25 * 1024 * 1024


def get_max_import_file_size():
    return getattr(
        settings, "BANK_TRANSACTION_IMPORT_MAX_FILE_SIZE", DEFAULT_MAX_IMPORT_FILE_SIZE
    )


def get_importer_choices():
    choices = [
        (identifier, importer.label)
        for identifier, importer in get_bank_transaction_importers().items()
    ]
    if process_csv_upload.has_listeners():
        choices.append((LEGACY_IMPORTER_CHOICE, _("Legacy bank importer (plugin)")))
    return choices


class BankTransactionImportForm(forms.Form):
    importer = forms.ChoiceField(label=_("Importer"), choices=get_importer_choices)
    source_file = forms.FileField(label=_("File"))

    def clean_source_file(self):
        source_file = self.cleaned_data["source_file"]
        max_size = get_max_import_file_size()
        if source_file.size > max_size:
            raise forms.ValidationError(
                _("The file is larger than the allowed maximum of %(size)s.")
                % {"size": filesizeformat(max_size)}
            )
        return source_file

    def save(self):
        importer = self.cleaned_data["importer"]
        return RealTransactionSource.objects.create(
            source_file=self.cleaned_data["source_file"],
            importer=None if importer == LEGACY_IMPORTER_CHOICE else importer,
        )


class UploadListView(ListView):
    template_name = "office/upload/list.html"
    context_object_name = "uploads"
    model = RealTransactionSource
    ordering = ("-pk",)
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        labels = {
            identifier: importer.label
            for identifier, importer in get_bank_transaction_importers().items()
        }
        for upload in context["uploads"]:
            upload.importer_label = (
                labels.get(upload.importer, upload.importer)
                if upload.importer
                else _("Legacy bank importer (plugin)")
            )
        return context


def process_source(request, source):
    """Process ``source`` and report the outcome as a user message."""
    try:
        result = source.process(user_or_context=request)
    except BankTransactionImportError as e:
        messages.error(
            request,
            _("The file could not be imported: %(error)s") % {"error": e},
        )
        return None
    except Exception as e:
        logger.exception("Processing of transaction source %s failed", source.pk)
        messages.error(
            request,
            _("The file was saved, but could not be processed: %(error)s")
            % {"error": e},
        )
        return None

    if hasattr(result, "imported_count"):
        messages.success(
            request,
            _(
                "Import successful. %(read)s transactions read, "
                "%(imported)s newly imported, %(duplicates)s already known."
            )
            % {
                "read": result.read_count,
                "imported": result.imported_count,
                "duplicates": result.duplicate_count,
            },
        )
    else:
        messages.success(request, _("The upload was processed successfully."))
    return result


class BankTransactionImportView(FormView):
    template_name = "office/upload/add.html"
    form_class = BankTransactionImportForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_importers"] = bool(get_importer_choices())
        context["max_file_size"] = filesizeformat(get_max_import_file_size())
        return context

    def form_valid(self, form):
        source = form.save()
        process_source(self.request, source)
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path


#: Backwards compatible alias for the former view name.
CsvUploadView = BankTransactionImportView


class UploadProcessView(DetailView):
    model = RealTransactionSource

    def post(self, request, *args, **kwargs):
        process_source(request, self.get_object())
        return redirect("office:finance.uploads.list")


class UploadMatchView(DetailView):
    model = RealTransactionSource

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        errors = success = 0
        for real_transaction in obj.transactions.all():
            try:
                real_transaction.process_transaction()
                success += 1
            except Exception:
                errors += 1
        messages.info(
            request,
            _("%(success)s successful matches, %(errors)s errors.")
            % {"success": success, "errors": errors},
        )
        return redirect("office:finance.uploads.list")
