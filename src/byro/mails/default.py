from django.utils.translation import gettext_lazy as _
from i18nfield.strings import LazyI18nString

WELCOME_MEMBER_SUBJECT = LazyI18nString.from_gettext(_("Welcome, latest member!"))
WELCOME_MEMBER_TEXT = LazyI18nString.from_gettext(_("""Hi,

welcome to {name}! You're now officially our latest member. Your member ID
is {number}. If you have any questions relating to your member fees or
you want to update your member data, please contact us at {contact}.

{additional_information}

Thanks,
the robo clerk"""))

WELCOME_OFFICE_SUBJECT = LazyI18nString.from_gettext(_("[byro] New member"))
WELCOME_OFFICE_TEXT = LazyI18nString.from_gettext(_("""Hi,

we have a new member: {member_name}

{additional_information}

Thanks,
the robo clerk"""))

LEAVE_MEMBER_SUBJECT = LazyI18nString.from_gettext(_("Goodbye!"))
LEAVE_MEMBER_TEXT = LazyI18nString.from_gettext(_("""Hi,

we are sorry that you will leave us at {end}.

{additional_information}

Thanks,
the robo clerk"""))

LEAVE_MEMBER_OFFICE_SUBJECT = LazyI18nString.from_gettext(
    _("[byro] Membership termination")
)
LEAVE_MEMBER_OFFICE_TEXT = LazyI18nString.from_gettext(_("""Hi,

{member_name} will leave us at {end}.

{additional_information}

Thanks,
the robo clerk"""))
RECORD_DISCLOSURE_SUBJECT = LazyI18nString.from_gettext(
    _("Your {association_name} data record (#{number})")
)
RECORD_DISCLOSURE_TEXT = LazyI18nString.from_gettext(_("""Hi,

We're writing you to let you know about the data we have currently stored about
yourself and your membership.

Your current balance is {balance}.

{data}

If these records are outdated or incorrect, please let us know as a response to
this email.

Thanks,
the robo clerk"""))
BALANCE_REMINDER_SUBJECT = LazyI18nString.from_gettext(_("Outstanding membership fees"))
BALANCE_REMINDER_TEXT = LazyI18nString.from_gettext(_("""Hello {name},

we wanted to let you know that within the time from {start}
to {end} you incurred unpaid liabilities in the amount of

   EUR {amount}

Please settle this amount as soon as possible, or let us
know if you think this email is incorrect."""))
DOCUMENT_DELIVERY_SUBJECT = LazyI18nString.from_gettext(
    _("[{association}] Your document")
)
DOCUMENT_DELIVERY_TEXT = LazyI18nString.from_gettext(_("""Hi, {name},

Please find attached a document we wanted to send you/that you requested.

Thank you,
{association}"""))
PGP_EXPIRY_REMINDER_SUBJECT = LazyI18nString.from_gettext(
    _("Your PGP key expires soon")
)
PGP_EXPIRY_REMINDER_TEXT = LazyI18nString.from_gettext(
    _(
        "Hello {name},\n\n"
        "the PGP key stored for your membership expires on {date}. "
        "Please send us an updated public key before it expires.\n"
    )
)
