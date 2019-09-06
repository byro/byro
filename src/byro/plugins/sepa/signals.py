from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from byro.members.signals import (
    leave_member_office_mail_information,
    new_member_mail_information,
    new_member_office_mail_information,
)


@receiver(new_member_mail_information)
def new_member_mail_info_sepa(sender, signal, **kwargs):
    if not (
        hasattr(sender, "profile_sepa")
        and sender.profile_sepa
        and sender.profile_sepa.is_usable
    ):
        return ""
    return _("Your SEPA mandate reference is {}.").format(
        sender.profile_sepa.mandate_reference
    )


@receiver(new_member_office_mail_information)
def new_member_office_mail_info_sepa(sender, signal, **kwargs):
    if not (
        hasattr(sender, "profile_sepa")
        and sender.profile_sepa
        and sender.profile_sepa.is_usable
    ):
        return ""
    if not sender.memberships.count() == 1:
        raise Exception("Cannot determine which membership to put in email!")
    membership = sender.memberships.first()
    data = {
        "iban": sender.profile_sepa.iban,
        "bic": sender.profile_sepa.bic,
        "institute": sender.profile_sepa.institute,
        "issue_date": sender.profile_sepa.issue_date.isoformat(),
        "name": sender.profile_sepa.fullname,
        "mandate_reference": sender.profile_sepa.mandate_reference,
        "mandate_reason": sender.profile_sepa.mandate_reason,
        "amount": "{:2f}".format(membership.amount),
        "interval": membership.get_interval_display(),
        "start": membership.start.isoformat(),
    }
    return _(
        """The new member has given us a SEPA mandate for {amount} ({interval}), starting on {start}:

Name: {name}
IBAN: {iban}
BIC: {bic} ({institute})
Mandate date: {issue_date}
Mandate reference: {mandate_reference}
Mandate reason: {mandate_reason}

"""
    ).format(**data)


@receiver(leave_member_office_mail_information)
def leave_member_office_mail_info_sepa(sender, signal, **kwargs):
    membership = sender
    member = sender.member

    if not (
        hasattr(member, "profile_sepa")
        and member.profile_sepa
        and member.profile_sepa.is_usable
    ):
        return ""
    data = {
        "number": member.number,
        "iban": member.profile_sepa.iban,
        "bic": member.profile_sepa.bic,
        "institute": member.profile_sepa.institute,
        "issue_date": member.profile_sepa.issue_date.isoformat(),
        "name": member.profile_sepa.fullname,
        "mandate_reference": member.profile_sepa.mandate_reference,
        "mandate_reason": member.profile_sepa.mandate_reason,
        "end": membership.end.isoformat(),
    }
    return _(
        """Please terminate SEPA mandate member number: {number} to {end}:

Name: {name}
IBAN: {iban}
BIC: {bic} ({institute})
Mandate date: {issue_date}
Mandate reference: {mandate_reference}
Mandate reason: {mandate_reason}

"""
    ).format(**data)
