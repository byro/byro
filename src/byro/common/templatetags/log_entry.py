from contextlib import suppress

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import register
from django.template.loader import TemplateDoesNotExist, get_template
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from byro.common.signals import log_formatters
from byro.documents.models import get_document_category_names

FORMATTER_REGISTRY = {}


def default_formatter(entry):
    with suppress(TemplateDoesNotExist):
        tmpl = get_template("log_entry/{}.html".format(entry.action_type))
        return tmpl.render({"log_entry": entry})

    data = dict(entry.data or {})
    data.pop("source", None)

    co = entry.content_object
    related_object = ""
    if co:
        url = None
        if hasattr(co, "get_absolute_url"):
            url = co.get_absolute_url()
        elif isinstance(co, get_user_model()):
            url = reverse("office:settings.users.detail", kwargs={"pk": co.pk})

        if url:
            related_object = mark_safe(
                ' (<a href="{}">{}</a>)'.format(escape(url), escape(str(co)))
            )
        else:
            related_object = mark_safe(" ({})".format(escape(co)))

    extra_data = ""
    if data:
        extra_data = " {}".format(escape(str(data)))

    return mark_safe(
        "{}{}{}".format(escape(str(entry.action_type)), related_object, extra_data)
    )


@register.filter(name="format_log_entry")
def format_log_entry(entry):
    if not FORMATTER_REGISTRY:
        for module, response in log_formatters.send_robust(sender=__name__):
            if response and not isinstance(response, Exception):
                FORMATTER_REGISTRY.update(response)

    return FORMATTER_REGISTRY.get(entry.action_type, default_formatter)(entry)


@register.filter(name="format_log_source")
def format_log_source(entry):
    user = ""
    if entry.user:
        user = mark_safe(
            '<span class="fa fa-user"></span> {}'.format(escape(entry.user))
        )

    source = entry.data.get("source", "")
    if source.startswith("internal: "):
        source = mark_safe(
            '<span class="fa fa-gears"></span> {}'.format(escape(source[10:]))
        )

    if entry.user:
        if entry.data.get("source", None) == str(entry.user):
            return user
        else:
            return mark_safe("{} (via {})".format(source, user))
    else:
        return source


@register.filter(name="format_log_object")
def format_log_object(obj, key=None):
    with suppress(Exception):
        if "object" in obj and "ref" in obj and "value" in obj:
            with suppress(Exception):
                content_object = ContentType.objects.get(
                    app_label=obj["ref"][0], model=obj["ref"][1]
                ).get_object_for_this_type(pk=obj["ref"][2])

                if obj["value"] == str(content_object):
                    url = content_object.get_absolute_url()
                    str_val = mark_safe(escape(str(obj["value"])))

                    if hasattr(content_object, "get_object_icon"):
                        icon = content_object.get_object_icon()
                    else:
                        icon = ""

                    if url:
                        return mark_safe(
                            '{}<a href="{}">{}</a>'.format(icon, escape(url), str_val)
                        )

            return mark_safe(
                "<i>{} object</i>: {!r}".format(
                    escape(str(obj["object"])), escape(str(obj["value"]))
                )
            )

        if key == "category" and "." in obj:
            cats = get_document_category_names()
            if obj in cats:
                return "{} ({})".format(cats[obj], obj)

        if key == "content_hash":
            parts = str(obj).split(":", 1)
            if len(parts) == 2:
                return mark_safe(
                    '{}: <tt title="{}">{} &hellip; {}</tt>'.format(
                        escape(parts[0]),
                        escape(parts[1]),
                        escape(parts[1][: (6 * 2)]),
                        escape(parts[1][-(6 * 2) :]),
                    )
                )

    return obj


@register.filter(name="items_sorted")
def items_sorted(data):
    return sorted(data)
