from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from byro.common.signals import unauthenticated_urls
from byro.members.models import Member
from byro.members.signals import (
    new_member_mail_information,
    new_member_office_mail_information,
)
from byro.office.signals import member_dashboard_tile, nav_event


@receiver(unauthenticated_urls)
def memberpage_unauthenticated_urls(sender, **kwargs):
    return (lambda a, b: b.view_name.startswith("public:memberpage:"),)


@receiver(nav_event)
def memberpage_primary(sender, **kwargs):
    request = sender
    if request.resolver_match and request.resolver_match.view_name.startswith(
        "public:memberpage"
    ):
        secret_token = request.resolver_match.kwargs.get("secret_token")
        if secret_token:
            kwargs = {"secret_token": secret_token}
            result = [
                {
                    "label": _("Member page"),
                    "url": reverse("public:memberpage:member.dashboard", kwargs=kwargs),
                    "active": request.resolver_match.view_name
                    == "public:memberpage.dashboard",
                }
            ]
            member = Member.all_objects.filter(
                profile_memberpage__secret_token=secret_token
            ).first()
            if member.is_active:
                result.append(
                    {
                        "label": _("Member list"),
                        "url": reverse("public:memberpage:member.list", kwargs=kwargs),
                        "active": request.resolver_match.view_name
                        == "public:memberpage:member.list",
                    }
                )
            return result
    return {}


@receiver(new_member_mail_information)
def new_member_mail_info_memberpage(sender, signal, **kwargs):
    url = sender.profile_memberpage.get_url()
    if url:
        return _("Your personal member page is at {link}").format(
            link=sender.profile_memberpage.get_url()
        )


@receiver(new_member_office_mail_information)
def new_member_office_mail_info_memberpage(sender, signal, **kwargs):
    url = sender.profile_memberpage.get_url()
    if url:
        return _("Their personal member page is at {link}").format(
            link=sender.profile_memberpage.get_url()
        )


@receiver(member_dashboard_tile)
def member_dashboard_page_link(sender, signal, member=None, **kwargs):
    if not member:
        return
    url = member.profile_memberpage.get_url()
    if url:
        return {"url": url, "title": _("Public profile")}
