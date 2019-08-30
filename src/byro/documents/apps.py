from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class DocumentsConfig(AppConfig):
    name = "byro.documents"

    class ByroPluginMeta:
        document_categories = {
            "byro.documents.misc": _("Miscellaneous document"),
            "byro.documents.registration_form": _("Registration form"),
        }
