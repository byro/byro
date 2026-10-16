from django.utils.translation import gettext_lazy as _
from i18nfield.strings import LazyI18nString

WELCOME_MEMBER_SUBJECT = LazyI18nString.from_gettext(_("Welcome to {name}"))
WELCOME_MEMBER_TEXT = LazyI18nString.from_gettext(_("""Hello {member_name},

Welcome to {name}! Your member number is {number}.

If you have questions about your membership fees or want to update your details, please contact us at {contact}.

{additional_information}"""))

WELCOME_OFFICE_SUBJECT = LazyI18nString.from_gettext(
    _("[byro] New member: {member_name}")
)
WELCOME_OFFICE_TEXT = LazyI18nString.from_gettext(
    _("""A new member has been added: {member_name}

{additional_information}""")
)

LEAVE_MEMBER_SUBJECT = LazyI18nString.from_gettext(_("End of your membership"))
LEAVE_MEMBER_TEXT = LazyI18nString.from_gettext(_("""Hello {member_name},

Your membership in {name} ends on {end}.

{additional_information}"""))

LEAVE_MEMBER_OFFICE_SUBJECT = LazyI18nString.from_gettext(
    _("[byro] End of membership: {member_name}")
)
LEAVE_MEMBER_OFFICE_TEXT = LazyI18nString.from_gettext(
    _("""The membership of {member_name} ends on {end}.

{additional_information}""")
)
RECORD_DISCLOSURE_SUBJECT = LazyI18nString.from_gettext(
    _("Your data at {association_name} (member number {number})")
)
RECORD_DISCLOSURE_TEXT = LazyI18nString.from_gettext(_("""Hello,

This is an overview of the data {association_name} currently stores about you and your membership.

Your current balance is {balance}. A negative balance means that fees are outstanding.

{data}

If anything is outdated or incorrect, please reply to this email and let us know."""))
BALANCE_REMINDER_SUBJECT = LazyI18nString.from_gettext(_("Outstanding membership fees"))
BALANCE_REMINDER_TEXT = LazyI18nString.from_gettext(
    _(
        """Hello {name},

According to our records, membership fees for the period from {start} to {end} are still outstanding:

    {amount}

Please pay this amount as soon as possible. If you think this is a mistake, please reply to this email."""
    )
)
DOCUMENT_DELIVERY_SUBJECT = LazyI18nString.from_gettext(
    _("Your document from {association}")
)
DOCUMENT_DELIVERY_TEXT = LazyI18nString.from_gettext(_("""Hello,

A document from {association} is attached to this email."""))
PGP_EXPIRY_REMINDER_SUBJECT = LazyI18nString.from_gettext(
    _("Your PGP key expires soon")
)
PGP_EXPIRY_REMINDER_TEXT = LazyI18nString.from_gettext(
    _(
        "Hello {name},\n\n"
        "The PGP key stored for your membership expires on {date}. "
        "Please send us an updated public key before it expires."
    )
)
# The closing block of every mail to a member, see byro.mails.footer. The
# signature separator is "-- " with a trailing space.
MEMBER_MAIL_FOOTER = LazyI18nString.from_gettext(
    _(
        "Best regards\n"
        "Your membership team\n"
        "\n"
        "-- \n"
        "{association_name}\n"
        "{association_address}\n"
        "{association_url}"
    )
)
