from django.utils.translation import ugettext_lazy as _
from i18nfield.strings import LazyI18nString


WELCOME_MEMBER_SUBJECT = LazyI18nString.from_gettext(_('Welcome, latest member!'))
WELCOME_MEMBER_TEXT = LazyI18nString.from_gettext(_('''Hi,

welcome to {name}! You're now officially our latest member. Your member ID
is {number}. If you have any questions relating to your member fees or
you want to update your member data, please contact us at {contact}.

{additional_information}
Thanks,
the robo clerk'''))
WELCOME_OFFICE_SUBJECT = LazyI18nString.from_gettext(_('[byro] New member'))
WELCOME_OFFICE_TEXT = LazyI18nString.from_gettext(_('''Hi,

we have a new member: {member_name}
{additional_information}

Thanks,
the robo clerk'''))
