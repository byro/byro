"""The footer below every mail to a member, ``Configuration.member_mail_footer``."""

from datetime import date
from unittest.mock import patch

import pytest
from dateutil.relativedelta import relativedelta
from django.utils.timezone import now
from django.utils.translation import override

from byro.common.models.configuration import Configuration
from byro.mails import default
from byro.mails.models import EMail, MailTemplate, RecipientType
from byro.mails.send import SendMailException, mail_send_task
from byro.members.models import FeeIntervals, Member, Membership

FOOTER_EN = (
    "Best regards\n"
    "Your membership team\n"
    "\n"
    "-- \n"
    "Association Name\n"
    "Street 1\n"
    "12345 Town\n"
    "https://association.example.org"
)
FOOTER_DE = (
    "Viele Grüße\n"
    "Deine Mitgliedsverwaltung\n"
    "\n"
    "-- \n"
    "Association Name\n"
    "Street 1\n"
    "12345 Town\n"
    "https://association.example.org"
)
FOOTER_PT_BR = (
    "Atenciosamente\n"
    "Equipe de gestão de associados\n"
    "\n"
    "-- \n"
    "Association Name\n"
    "Street 1\n"
    "12345 Town\n"
    "https://association.example.org"
)


@pytest.fixture
def association(configuration):
    configuration.address = "Street 1\n12345 Town"
    configuration.url = "https://association.example.org"
    configuration.save()
    return configuration


def set_footer(value, language=None):
    config = Configuration.get_solo()
    config.member_mail_footer = value
    if language:
        config.language = language
    config.save()
    return config


def activate(member):
    return Membership.objects.create(
        member=member,
        start=now().date() - relativedelta(months=1),
        amount=20,
        interval=FeeIntervals.MONTHLY,
    )


def member_mail(member, text="Text"):
    mail = EMail.for_member(member, subject="Test", text=text)
    mail.save()
    return mail


def member_page_url(member):
    return member.profile_memberpage.get_url()


@pytest.mark.django_db
def test_installation_has_the_default_footer(association, member, mailoutbox):
    member_mail(member).send()

    assert mailoutbox[0].body == "Text\n\n" + FOOTER_EN


@pytest.mark.django_db
def test_null_is_the_built_in_default(association, member, mailoutbox):
    set_footer(None)

    member_mail(member).send()

    assert Configuration.get_solo().member_mail_footer.data is None
    assert mailoutbox[0].body == "Text\n\n" + FOOTER_EN


@pytest.mark.django_db
def test_default_footer_has_no_member_page_link(association, member, mailoutbox):
    member_mail(member).send()

    assert member_page_url(member) not in mailoutbox[0].body


@pytest.mark.django_db
def test_mail_to_an_address_has_no_footer(association, member, mailoutbox):
    set_footer({"en": "Footer {association_name} {member_page_url}"})
    mail = EMail.objects.create(to=member.email, subject="Test", text="Text")

    mail.send()

    assert mailoutbox[0].body == "Text"


@pytest.mark.django_db
def test_configured_footer_fills_in_every_placeholder(association, member, mailoutbox):
    set_footer(
        {
            "en": "Thanks!\n{association_name}\n{association_address}\n"
            "{association_url}\nYour page: {member_page_url}"
        }
    )

    member_mail(member).send()

    assert mailoutbox[0].body == (
        "Text\n\nThanks!\nAssociation Name\nStreet 1\n12345 Town\n"
        f"https://association.example.org\nYour page: {member_page_url(member)}"
    )


@pytest.mark.django_db
def test_literal_braces_in_the_footer(association, member, mailoutbox):
    set_footer({"en": "{{literal}} {association_name}"})

    member_mail(member).send()

    assert mailoutbox[0].body == "Text\n\n{literal} Association Name"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "text", ("Text\n", "Text\n\n", "Text\n\n\n", "Text\r\n\r\n"), ids=repr
)
def test_line_breaks_at_the_end_of_the_text_leave_one_empty_line(
    association, member, mailoutbox, text
):
    member_mail(member, text=text).send()

    assert mailoutbox[0].body == "Text\n\n" + FOOTER_EN


@pytest.mark.django_db
def test_only_line_breaks_are_removed_before_the_footer(
    association, member, mailoutbox
):
    member_mail(member, text="Text  \n\n").send()

    assert mailoutbox[0].body == "Text  \n\n" + FOOTER_EN


@pytest.mark.django_db
def test_default_template_with_empty_additional_information(
    association, member, mailoutbox
):
    template = MailTemplate(
        subject=default.LEAVE_MEMBER_SUBJECT, text=default.LEAVE_MEMBER_TEXT
    )
    mail = template.to_mail(
        member=member,
        context={
            "name": "Association Name",
            "contact": "office@example.org",
            "number": member.number,
            "member_name": member.name,
            "end": date(2026, 12, 31),
            "additional_information": "",
        },
    )

    mail.send()

    assert mailoutbox[0].body == (
        f"Hello {member.name},\n\n"
        "Your membership in Association Name ends on 2026-12-31.\n\n" + FOOTER_EN
    )


@pytest.mark.django_db
def test_text_without_footer_keeps_its_line_breaks(configuration, member, mailoutbox):
    set_footer({})
    member_mail(member, text="Text\n\n").send()
    EMail.objects.create(to=member.email, subject="Test", text="Text\n\n").send()

    assert [mail.body for mail in mailoutbox] == ["Text\n\n", "Text\n\n"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "footer",
    ({}, {"en": "  \n "}, {"en": "{association_url}"}),
    ids=("empty", "whitespace", "renders-empty"),
)
def test_footer_without_text_adds_nothing(configuration, member, mailoutbox, footer):
    set_footer(footer)

    member_mail(member).send()

    assert mailoutbox[0].body == "Text"


@pytest.mark.django_db
def test_disabled_footer_is_off_in_every_language(configuration, member, mailoutbox):
    set_footer({}, language="de")

    member_mail(member).send()

    assert mailoutbox[0].body == "Text"


@pytest.mark.django_db
def test_settings_that_are_not_filled_in_leave_no_none(member, mailoutbox):
    config = Configuration.get_solo()
    config.name = None
    config.address = None
    config.url = None
    config.mail_from = "associationname@example.com"
    config.save()

    member_mail(member).send()

    body = mailoutbox[0].body
    assert "None" not in body
    assert body == "Text\n\nBest regards\nYour membership team\n\n-- "


@pytest.mark.django_db
def test_footer_does_not_change_the_stored_mail(association, member, mailoutbox):
    mail = member_mail(member)

    mail.send()

    mail.refresh_from_db()
    assert mail.text == "Text"


@pytest.mark.django_db
@pytest.mark.parametrize("to_type", (RecipientType.MEMBER, RecipientType.ALL_MEMBERS))
def test_every_member_gets_their_own_member_page_url(
    member_page_url_footer, mailoutbox, to_type
):
    family = [
        Member.objects.create(email="family@example.org", number="10", name="A"),
        Member.objects.create(email="family@example.org", number="11", name="B"),
    ]
    mail = EMail.objects.create(to_type=to_type, subject="Test", text="Text")
    if to_type == RecipientType.MEMBER:
        mail.set_member_recipients(family)
    else:
        for member in family:
            activate(member)

    mail.send()

    bodies = {message.body for message in mailoutbox}
    assert bodies == {
        f"Text\n\nMember page: {member_page_url(member)}" for member in family
    }
    mail.refresh_from_db()
    assert mail.delivered_to_members == {
        str(member.pk): "family@example.org" for member in family
    }


@pytest.mark.django_db
@pytest.mark.parametrize("stored", ("migrated", "null"))
@pytest.mark.parametrize(
    "language,expected",
    (("de", FOOTER_DE), ("en", FOOTER_EN), ("pt-br", FOOTER_PT_BR)),
)
def test_footer_is_in_the_language_of_the_organization(
    association, member, mailoutbox, stored, language, expected
):
    config = Configuration.get_solo()
    config.language = language
    if stored == "null":
        config.member_mail_footer = None
    config.save()

    # whatever language is active while sending, as in a request or a command
    for active in ("en", "de"):
        with override(active):
            member_mail(member).send()

    assert [message.body for message in mailoutbox] == [
        "Text\n\n" + expected,
        "Text\n\n" + expected,
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "footer",
    (
        "{nmae}",
        "{association.name}",
        "{",
        "}",
        "{0}",
        "{association_name:%d}",
    ),
)
def test_invalid_footer_stops_the_mail_before_any_delivery(
    configuration, mailoutbox, footer
):
    set_footer({"en": footer})
    members = [
        Member.objects.create(email=f"{number}@example.org", number=number)
        for number in ("10", "11")
    ]
    for member in members:
        activate(member)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )

    with patch("byro.mails.send.mail_send_task", wraps=mail_send_task) as send_task:
        with pytest.raises(SendMailException) as error:
            mail.send()

    assert "footer of mails to members" in str(error.value)
    assert "Available placeholders: {association_name}" in str(error.value)
    assert send_task.call_count == 0
    assert mailoutbox == []
    mail.refresh_from_db()
    assert mail.sent is None
    assert mail.delivered_to == []
    assert mail.delivered_to_members == {}
    assert not mail.members.exists()


@pytest.mark.django_db
def test_invalid_footer_does_not_stop_mails_to_an_address(configuration, mailoutbox):
    set_footer({"en": "{nmae}"})
    mail = EMail.objects.create(to="office@example.org", subject="Test", text="Text")

    mail.send()

    assert mailoutbox[0].body == "Text"
