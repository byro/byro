from django.utils.translation import ugettext_lazy as _
from i18nfield.strings import LazyI18nString

WELCOME_MEMBER_SUBJECT = LazyI18nString.from_gettext(_("Welcome, latest member!"))
WELCOME_MEMBER_TEXT = LazyI18nString.from_gettext(
    _(
        """Hi,

welcome to {name}! You're now officially our latest member. Your member ID
is {number}. If you have any questions relating to your member fees or
you want to update your member data, please contact us at {contact}.

{additional_information}

Thanks,
the robo clerk"""
    )
)

WELCOME_OFFICE_SUBJECT = LazyI18nString.from_gettext(_("[byro] New member"))
WELCOME_OFFICE_TEXT = LazyI18nString.from_gettext(
    _(
        """Hi,

we have a new member: {member_name}

{additional_information}

Thanks,
the robo clerk"""
    )
)

LEAVE_MEMBER_SUBJECT = LazyI18nString.from_gettext(_("Goodbye!"))
LEAVE_MEMBER_TEXT = LazyI18nString.from_gettext(
    _(
        """Hi,

we are sorry that you will leave us at {end}.

{additional_information}

Thanks,
the robo clerk"""
    )
)

LEAVE_MEMBER_OFFICE_SUBJECT = LazyI18nString.from_gettext(
    _("[byro] Membership termination")
)
LEAVE_MEMBER_OFFICE_TEXT = LazyI18nString.from_gettext(
    _(
        """Hi,

{member_name} will leave us at {end}.

{additional_information}

Thanks,
the robo clerk"""
    )
)
RECORD_DISCLOSURE_SUBJECT = LazyI18nString.from_gettext(
    (_("Your {association_name} data record (#{number})"))
)
RECORD_DISCLOSURE_TEXT = LazyI18nString.from_gettext(
    _(
        """Hi,

We're writing you to let you know about the data we have currently stored about
yourself and your membership.

Your current balance is {balance}.

{data}

If these records are outdated or incorrect, please let us know as a response to
this email.

Thanks,
the robo clerk"""
    )
)
