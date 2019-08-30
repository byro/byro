from django.template.defaultfilters import register
from django.utils.translation import ugettext_lazy as _

from byro.documents.models import get_document_category_names


@register.filter(name="translate_document_category")
def translate_document_category(data):
    return get_document_category_names().get(data, _("Unknown document type"))
