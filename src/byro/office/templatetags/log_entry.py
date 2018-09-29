from django.contrib.auth import get_user_model
from django.template.defaultfilters import register
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from byro.common.signals import log_formatters

FORMATTER_REGISTRY = {}


def default_formatter(entry):
    data = dict(entry.data)
    data.pop('source')

    co = entry.content_object
    related_object = ""
    if co:
        url = None
        if hasattr(co, 'get_absolute_url'):
            url = co.get_absolute_url()
        elif isinstance(co, get_user_model()):
            url = reverse('office:settings.users.detail', kwargs={'pk': co.pk})

        if url:
            related_object = mark_safe('(<a href="{}">{}</a>)'.format(escape(url), escape(str(co))))
        else:
            related_object = mark_safe('({})'.format(escape(co)))

    extra_data = ""
    if data:
        extra_data = " {}".format(escape(str(data)))

    return mark_safe("{}{}{}".format(escape(str(entry.action_type)), related_object, extra_data))


@register.filter(name='format_log_entry')
def format_log_entry(entry):
    if not FORMATTER_REGISTRY:
        for module, response in log_formatters.send_robust(sender=__name__):
            if response and not isinstance(response, Exception):
                FORMATTER_REGISTRY.update(response)

    return FORMATTER_REGISTRY.get(entry.action_type, default_formatter)(entry)


@register.filter(name='format_log_source')
def format_log_source(entry):
    if entry.user:
        if entry.data.get('source', None) == str(entry.user):
            return entry.user
        else:
            return "{} (via {})".format(entry.data['source'], entry.user)
    else:
        return entry.data['source']
