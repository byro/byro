"""The footer byro adds below every mail to a member.

The footer is ``Configuration.member_mail_footer``. Stored as ``NULL`` it is
the built-in default, stored without any text (``{}``) there is no footer.
Mails to an address never get it.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override

from byro.mails import default

MEMBER_MAIL_FOOTER_PLACEHOLDERS = (
    "association_name",
    "association_address",
    "association_url",
    "member_page_url",
)


def get_member_mail_footer(config):
    """The footer as configured, ``None`` for the built-in default.

    i18nfield loads ``NULL`` as a ``LazyI18nString`` without data, a new
    configuration that was never saved has ``None`` here.
    """
    footer = config.member_mail_footer
    if footer is None or footer.data is None:
        return None
    return footer


def get_member_mail_footer_text(config):
    """The footer text in the language of the organization, as mail texts
    are rendered in it. Empty if there is no footer."""
    footer = get_member_mail_footer(config)
    if footer is None:
        # not ``or``: a footer without text is false as well
        footer = default.MEMBER_MAIL_FOOTER
    with override(config.language):
        return str(footer)


def member_mail_footer_context(config, member_page_url):
    """The values of the placeholders. Settings that are not filled in are
    empty, never ``None``."""
    return {
        "association_name": config.name or "",
        "association_address": config.address or "",
        "association_url": config.url or "",
        "member_page_url": member_page_url,
    }


def render_member_mail_footer(text, context):
    """Fill in the placeholders of a footer text.

    Line breaks at the end are removed, so that settings that are not filled
    in leave no empty lines at the end of the mail. Spaces are kept, the
    signature separator "-- " ends with one. Raises a ValidationError if the
    text cannot be rendered.
    """
    available = ", ".join("{%s}" % name for name in MEMBER_MAIL_FOOTER_PLACEHOLDERS)
    try:
        return text.format(**context).rstrip("\r\n")
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


def check_member_mail_footer(text, config):
    """Raise a ValidationError if ``text`` cannot be used as the footer.

    The values have the types of the real ones (all text), so a footer that
    passes this check can be rendered for every member.
    """
    render_member_mail_footer(
        text,
        member_mail_footer_context(
            config, member_page_url="https://example.org/p/member/token/"
        ),
    )
