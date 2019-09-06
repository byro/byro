from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BookkeepingConfig(AppConfig):
    name = "byro.bookkeeping"

    class ByroPluginMeta:
        document_categories = {
            "byro.bookkeeping.receipt": _("Receipt"),
            "byro.bookkeeping.invoice": _("Invoice"),
            "byro.bookkeeping.account.statement": _("Statement"),
        }
