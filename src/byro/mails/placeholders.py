"""The placeholders the core mail templates are rendered with.

Each template that byro sends itself is configured in a ``Configuration``
field, and the code that sends it passes the values below. A template edited
in the office is checked against the values of every field it is configured
in. The values have the types of the real ones, so a template that passes the
check can also use their format specifications, such as ``{end:%d.%m.%Y}``.
"""

import datetime
import string

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

_TEXT = "text"
_DATE = datetime.date(2026, 12, 31)

#: Configuration field of the template -> the values it is rendered with
CORE_TEMPLATE_CONTEXTS = {
    "welcome_member_template": {
        "name": _TEXT,
        "contact": _TEXT,
        "number": _TEXT,
        "member_name": _TEXT,
        "additional_information": _TEXT,
    },
    "welcome_office_template": {
        "member_name": _TEXT,
        "additional_information": _TEXT,
    },
    "leave_member_template": {
        "name": _TEXT,
        "contact": _TEXT,
        "number": _TEXT,
        "member_name": _TEXT,
        "end": _DATE,
        "additional_information": _TEXT,
    },
    "leave_office_template": {
        "member_name": _TEXT,
        "end": _DATE,
        "additional_information": _TEXT,
    },
    "record_disclosure_template": {
        "association_name": _TEXT,
        "data": _TEXT,
        "number": _TEXT,
        "balance": _TEXT,
    },
    "balance_reminder_template": {
        "name": _TEXT,
        "start": _DATE,
        "end": _DATE,
        "amount": _TEXT,
    },
    "document_delivery_template": {
        "name": _TEXT,
        "association": _TEXT,
    },
    "pgp_expiry_reminder_template": {
        "name": _TEXT,
        "date": _DATE,
    },
}


#: (configuration field, template field) pairs that are sent as they are written
NOT_RENDERED = {
    # the balance run fills in only the text, see byro.office.views.members
    ("balance_reminder_template", "subject"),
}


def template_contexts(template, config, field):
    """The contexts ``field`` of ``template`` is rendered with, one per
    configuration field the template is set in.

    ``None`` for a template byro does not send itself, whose placeholders are
    not known.
    """
    configured = [
        name
        for name in CORE_TEMPLATE_CONTEXTS
        if template.pk is not None and getattr(config, f"{name}_id") == template.pk
    ]
    if not configured:
        return None
    return [
        CORE_TEMPLATE_CONTEXTS[name]
        for name in configured
        if (name, field) not in NOT_RENDERED
    ]


def check_template_text(text, context):
    """Raise a ValidationError if ``text`` cannot be rendered with ``context``.

    Without a context, only the syntax is checked, since the placeholders
    of a template byro does not send itself are not known.
    """
    if context is None:
        try:
            list(string.Formatter().parse(text))
        except ValueError:
            raise ValidationError(
                _(
                    "The text contains an invalid placeholder. Write %(open)s and %(close)s for literal curly braces."
                ),
                code="invalid_placeholder",
                params={"open": "{{", "close": "}}"},
            )
        return
    available = ", ".join("{%s}" % name for name in context)
    try:
        text.format(**context)
    except KeyError as e:
        raise ValidationError(
            _(
                "Unknown placeholder: %(placeholder)s. Available placeholders: %(available)s"
            ),
            code="unknown_placeholder",
            params={"placeholder": "{%s}" % e.args[0], "available": available},
        )
    except (IndexError, AttributeError, ValueError, TypeError):
        raise ValidationError(
            _(
                "The text contains an invalid placeholder. Available placeholders: %(available)s. Write %(open)s and %(close)s for literal curly braces."
            ),
            code="invalid_placeholder",
            params={"available": available, "open": "{{", "close": "}}"},
        )
