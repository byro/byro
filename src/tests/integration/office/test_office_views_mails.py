import re
from unittest.mock import patch

import pytest
from dateutil.relativedelta import relativedelta
from django.shortcuts import reverse
from django.utils.timezone import now

from byro.common.models.configuration import Configuration
from byro.mails.models import EMail, PGPConfiguration, PGPPolicy, RecipientType
from byro.mails.send import SendMailException, mail_send_task
from byro.members.models import (
    FeeIntervals,
    Member,
    MemberBalance,
    Membership,
    MemberTypes,
)


@pytest.mark.django_db
def test_outbox_send_shows_error_when_pgp_blocks_mail(
    member, logged_in_client, configuration
):
    pgp_config = PGPConfiguration.get_solo()
    pgp_config.encryption_enabled = True
    pgp_config.missing_key_policy = PGPPolicy.BLOCK
    pgp_config.save()
    mail = EMail.objects.create(
        to_type=RecipientType.MEMBER, subject="Test", text="Text"
    )
    mail.members.add(member)

    response = logged_in_client.get(
        reverse("office:mails.mail.send", kwargs={"pk": mail.pk})
    )

    assert response.status_code == 302
    assert response.url == reverse("office:mails.outbox.list")
    mail.refresh_from_db()
    assert mail.sent is None


@pytest.mark.django_db
def test_outbox_send_continues_after_a_pgp_failure(
    member, logged_in_client, configuration
):
    pgp_config = PGPConfiguration.get_solo()
    pgp_config.encryption_enabled = True
    pgp_config.missing_key_policy = PGPPolicy.BLOCK
    pgp_config.save()
    blocked_mail = EMail.objects.create(
        to_type=RecipientType.MEMBER, subject="Blocked", text="Text"
    )
    blocked_mail.members.add(member)
    deliverable_mail = EMail.objects.create(
        to="office@example.org", subject="Deliverable", text="Text"
    )

    response = logged_in_client.get(reverse("office:mails.outbox.send"))

    assert response.status_code == 302
    blocked_mail.refresh_from_db()
    deliverable_mail.refresh_from_db()
    assert blocked_mail.sent is None
    assert deliverable_mail.sent is not None


@pytest.mark.django_db
def test_settings_show_private_signing_key_upload(superuser_client, configuration):
    response = superuser_client.get(reverse("office:settings.base"))
    content = response.content.decode()

    assert response.status_code == 200, content
    assert 'enctype="multipart/form-data"' in content
    assert "Upload private signing key" in content
    assert "This field is required." not in content
    assert "Encryption" in content
    assert "Signing" in content
    assert "PGP signing" in content
    assert "PGP encryption" in content
    assert "Advanced key management" in content
    assert "Expiry reminders" in content
    assert "No signing key configured." in content


SHARED_ADDRESS = "family@example.org"


@pytest.fixture
def family(configuration):
    """Two members sharing one address."""
    return (
        Member.objects.create(email=SHARED_ADDRESS, number="10", name="Member A"),
        Member.objects.create(email=SHARED_ADDRESS, number="11", name="Member B"),
    )


def member_mail(*members, **kwargs):
    kwargs.setdefault("subject", "Test")
    kwargs.setdefault("text", "Text")
    mail = EMail.objects.create(to_type=RecipientType.MEMBER, **kwargs)
    mail.members.add(*members)
    return mail


def compose_data(**kwargs):
    return {"subject": "Subject", "text": "Text", "action": "save", **kwargs}


def checked_recipient_type(content):
    (checked,) = re.findall(r'name="to_type" id="to_type__(\w+)"[^>]*?checked', content)
    return checked


def selected_member(content):
    """The member the browser shows as selected: the option marked as
    selected, otherwise the first option of the select."""
    select = content[content.index('name="to_member"') :]
    select = select[: select.index("</select>")]
    selected = re.findall(r'<option value="(\d*)" selected', select)
    assert len(selected) <= 1
    if not selected:
        selected = re.findall(r'<option value="(\d*)"', select)[:1]
    return int(selected[0]) if selected[0] else None


NO_MEMBER_WARNING = "No valid member is selected as the recipient of this mail."


@pytest.mark.django_db
def test_compose_to_a_specific_address_does_not_become_a_member_mail(
    member, logged_in_client, configuration
):
    response = logged_in_client.post(
        reverse("office:mails.compose"),
        compose_data(
            to_type="addr",
            to=member.email,
            to_member=member.pk,
            cc="cc@example.org",
            bcc="bcc@example.org",
            reply_to="reply@example.org",
        ),
    )

    assert response.status_code == 302, response.content.decode()
    mail = EMail.objects.get()
    assert mail.to_type == RecipientType.ADDRESS
    assert mail.to == member.email
    assert (mail.cc, mail.bcc, mail.reply_to) == (
        "cc@example.org",
        "bcc@example.org",
        "reply@example.org",
    )
    assert mail.sent is None
    assert not mail.members.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("addressed", (0, 1))
def test_compose_to_a_member_keeps_the_selected_member(
    family, addressed, logged_in_client
):
    recipient = family[addressed]

    response = logged_in_client.post(
        reverse("office:mails.compose"),
        compose_data(to_type="member", to_member=recipient.pk, to="x@example.org"),
    )

    assert response.status_code == 302, response.content.decode()
    mail = EMail.objects.get()
    assert mail.to_type == RecipientType.MEMBER
    assert mail.to == ""
    assert mail.get_member_recipients() == [recipient]


@pytest.mark.django_db
@pytest.mark.parametrize("addressed", (0, 1))
def test_compose_and_send_to_a_member_of_a_shared_address(
    family, addressed, logged_in_client, mailoutbox
):
    recipient, other = family[addressed], family[1 - addressed]

    response = logged_in_client.post(
        reverse("office:mails.compose"),
        compose_data(to_type="member", to_member=recipient.pk, action="send"),
    )

    assert response.status_code == 302, response.content.decode()
    mail = EMail.objects.get()
    assert mail.sent is not None
    assert mail.delivered_to_members == {str(recipient.pk): SHARED_ADDRESS}
    assert [message.to for message in mailoutbox] == [[SHARED_ADDRESS]]
    assert recipient.profile_memberpage.get_url() in mailoutbox[0].body
    assert other.profile_memberpage.get_url() not in mailoutbox[0].body
    assert list(recipient.emails.all()) == [mail]
    assert not other.emails.exists()


@pytest.mark.django_db
def test_compose_to_all_members(member, logged_in_client, configuration):
    response = logged_in_client.post(
        reverse("office:mails.compose"),
        compose_data(to_type="all", to="x@example.org", to_member=member.pk),
    )

    assert response.status_code == 302, response.content.decode()
    mail = EMail.objects.get()
    assert mail.to_type == RecipientType.ALL_MEMBERS
    assert mail.to == ""
    assert not mail.members.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data",
    (
        {"to_type": "addr", "to": ""},
        {"to_type": "addr", "to": "special:all"},
        {"to_type": "addr", "to": "special:member:1"},
        {"to_type": "member"},
        {"to_type": "other", "to": "x@example.org"},
    ),
)
def test_compose_rejects_incomplete_recipients(
    member, logged_in_client, configuration, data
):
    response = logged_in_client.post(
        reverse("office:mails.compose"), compose_data(action="send", **data)
    )

    assert response.status_code == 200
    assert not EMail.objects.exists()


@pytest.mark.django_db
def test_compose_link_from_the_member_page_preselects_the_member(
    family, logged_in_client
):
    member_a, member_b = family

    response = logged_in_client.get(
        reverse("office:members.mails", kwargs={"pk": member_b.pk})
    )
    content = response.content.decode()
    link = (
        f"{reverse('office:mails.compose')}?to_type=member&amp;to_member={member_b.pk}"
    )
    assert link in content

    response = logged_in_client.get(link.replace("&amp;", "&"))
    content = response.content.decode()

    assert response.status_code == 200
    assert checked_recipient_type(content) == "member"
    assert selected_member(content) == member_b.pk


@pytest.mark.django_db
def test_compose_form_defaults_to_a_specific_address(logged_in_client, configuration):
    response = logged_in_client.get(reverse("office:mails.compose"))

    assert response.status_code == 200
    assert checked_recipient_type(response.content.decode()) == "addr"


@pytest.mark.django_db
@pytest.mark.parametrize("addressed", (0, 1))
def test_member_draft_opens_with_its_member(family, addressed, logged_in_client):
    mail = member_mail(family[addressed])

    response = logged_in_client.get(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk})
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert checked_recipient_type(content) == "member"
    assert selected_member(content) == family[addressed].pk


@pytest.mark.django_db
def test_member_draft_keeps_a_member_that_is_not_selectable_anymore(
    family, logged_in_client
):
    member_a, member_b = family
    member_b.email = ""
    member_b.save()
    mail = member_mail(member_b)
    url = reverse("office:mails.mail.view", kwargs={"pk": mail.pk})

    response = logged_in_client.get(url)

    assert selected_member(response.content.decode()) == member_b.pk

    response = logged_in_client.post(
        url, compose_data(to_type="member", to_member=member_b.pk)
    )

    assert response.status_code == 302, response.content.decode()
    assert mail.get_member_recipients() == [member_b]


@pytest.mark.django_db
@pytest.mark.parametrize("to_type", ("addr", "all"))
def test_other_drafts_open_with_their_recipient_type(
    member, logged_in_client, configuration, to_type
):
    mail = EMail.objects.create(
        to_type=to_type,
        to="one@example.org" if to_type == "addr" else "",
        subject="Test",
        text="Text",
    )

    response = logged_in_client.get(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk})
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert checked_recipient_type(content) == to_type
    assert ('value="one@example.org"' in content) is (to_type == "addr")


@pytest.mark.django_db
def test_member_draft_can_be_changed_to_another_member(family, logged_in_client):
    member_a, member_b = family
    mail = member_mail(member_a)

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(to_type="member", to_member=member_b.pk),
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.to_type == RecipientType.MEMBER
    assert mail.subject == "Subject"
    assert mail.get_member_recipients() == [member_b]
    assert not member_a.emails.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data,to",
    (
        ({"to_type": "addr", "to": "one@example.org"}, "one@example.org"),
        ({"to_type": "all"}, ""),
    ),
)
def test_member_draft_can_be_changed_to_another_recipient_type(
    family, logged_in_client, data, to
):
    member_a, member_b = family
    mail = member_mail(member_a)

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(to_member=member_a.pk, **data),
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.to_type == data["to_type"]
    assert mail.to == to
    assert not mail.members.exists()


@pytest.mark.django_db
def test_address_draft_can_be_changed_to_a_member(family, logged_in_client):
    member_a, member_b = family
    mail = EMail.objects.create(to=SHARED_ADDRESS, subject="Test", text="Text")

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(to_type="member", to_member=member_b.pk, to=SHARED_ADDRESS),
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.to_type == RecipientType.MEMBER
    assert mail.to == ""
    assert mail.get_member_recipients() == [member_b]


@pytest.mark.django_db
def test_draft_with_several_member_recipients_keeps_them(family, logged_in_client):
    member_a, member_b = family
    mail = member_mail(member_a, member_b)
    url = reverse("office:mails.mail.view", kwargs={"pk": mail.pk})

    response = logged_in_client.get(url)
    content = response.content.decode()

    assert response.status_code == 200
    assert "Member A &lt;family@example.org&gt;, Member B &lt;" in content
    assert 'name="to_type"' not in content

    response = logged_in_client.post(
        url, compose_data(to_type="addr", to="one@example.org", to_member=member_a.pk)
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.subject == "Subject"
    assert mail.to_type == RecipientType.MEMBER
    assert mail.to == ""
    assert mail.get_member_recipients() == [member_a, member_b]


@pytest.mark.django_db
def test_outbox_and_sent_mails_show_the_recipients(family, logged_in_client):
    member_a, member_b = family
    for sent in (None, now()):
        member_mail(member_b, sent=sent)
        EMail.objects.create(
            to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text", sent=sent
        )
        EMail.objects.create(
            to="one@example.org", subject="Test", text="Text", sent=sent
        )

    for url_name in ("office:mails.outbox.list", "office:mails.sent"):
        response = logged_in_client.get(reverse(url_name))
        content = response.content.decode()

        assert response.status_code == 200
        assert "<td>Member B &lt;family@example.org&gt;</td>" in content
        assert "Member A" not in content
        assert "<td>All members</td>" in content
        assert "<td>one@example.org</td>" in content
        assert "special:" not in content


@pytest.mark.django_db
def test_sent_member_mail_shows_its_member(family, logged_in_client):
    member_a, member_b = family
    mail = member_mail(member_b, sent=now())

    response = logged_in_client.get(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk})
    )
    content = response.content.decode()

    assert response.status_code == 200
    # a sent mail shows its recipient, it does not offer a selection
    assert "Member B &lt;family@example.org&gt;" in content
    assert "Member A" not in content
    assert 'name="to_type"' not in content
    assert 'name="to_member"' not in content


@pytest.mark.django_db
def test_member_mail_history_only_lists_the_mails_of_the_member(
    family, logged_in_client
):
    member_a, member_b = family
    member_mail(member_a, subject="Mail for A", sent=now())
    member_mail(member_b, subject="Mail for B", sent=now())
    EMail.objects.create(
        to=SHARED_ADDRESS, subject="Mail for the address", text="Text", sent=now()
    )

    for url_name in ("office:members.mails", "office:members.timeline"):
        response = logged_in_client.get(reverse(url_name, kwargs={"pk": member_a.pk}))
        content = response.content.decode()

        assert response.status_code == 200
        assert "Mail for A" in content
        assert "Member A &lt;family@example.org&gt;" in content
        assert "Mail for B" not in content
        assert "Mail for the address" not in content


@pytest.mark.django_db
def test_copy_of_a_sent_member_mail_keeps_the_member(family, logged_in_client):
    member_a, member_b = family
    mail = member_mail(member_b, sent=now())

    response = logged_in_client.get(
        reverse("office:mails.mail.copy", kwargs={"pk": mail.pk})
    )

    draft = EMail.objects.exclude(pk=mail.pk).get()
    assert response.status_code == 302
    assert response.url == reverse("office:mails.mail.view", kwargs={"pk": draft.pk})
    assert draft.sent is None
    assert draft.get_member_recipients() == [member_b]


@pytest.mark.django_db
def test_leftover_special_draft_can_be_opened_but_not_sent(
    member, logged_in_client, configuration, mailoutbox
):
    mail = EMail.objects.create(
        to="special:member:9999", subject="Leftover", text="Text"
    )

    response = logged_in_client.get(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk})
    )
    assert response.status_code == 200

    response = logged_in_client.get(
        reverse("office:mails.mail.send", kwargs={"pk": mail.pk}), follow=True
    )

    assert "has to be reviewed" in response.content.decode()
    mail.refresh_from_db()
    assert mail.sent is None
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_outbox_sends_member_mails_of_a_shared_address_to_each_member(
    family, logged_in_client, mailoutbox
):
    member_a, member_b = family
    mail_a = member_mail(member_a)
    mail_b = member_mail(member_b)

    response = logged_in_client.get(reverse("office:mails.outbox.send"))

    assert response.status_code == 302
    mail_a.refresh_from_db()
    mail_b.refresh_from_db()
    assert mail_a.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert mail_b.delivered_to_members == {str(member_b.pk): SHARED_ADDRESS}
    assert len(mailoutbox) == 2


@pytest.mark.django_db
def test_welcome_mail_is_addressed_to_the_new_member(
    member, logged_in_client, configuration
):
    configuration.registration_form = [
        {"name": name, "position": position}
        for position, name in enumerate(
            (
                "member__number",
                "member__name",
                "member__email",
                "membership__start",
                "membership__interval",
                "membership__amount",
            ),
            start=1,
        )
    ]
    configuration.save()

    response = logged_in_client.post(
        reverse("office:members.add"),
        {
            "member__number": "2323",
            "member__name": "Torsten Est",
            "member__email": member.email,
            "membership__start": str(now().date()),
            "membership__interval": "1",
            "membership__amount": "10",
        },
        follow=True,
    )

    assert response.status_code == 200
    new_member = Member.objects.get(number="2323")
    assert new_member.email == member.email
    config = Configuration.get_solo()
    welcome = EMail.objects.get(template=config.welcome_member_template)
    assert welcome.to_type == RecipientType.MEMBER
    assert welcome.to == ""
    assert welcome.get_member_recipients() == [new_member]
    # the notification for the office stays a plain address
    office = EMail.objects.get(template=config.welcome_office_template)
    assert office.to_type == RecipientType.ADDRESS
    assert office.to == config.backoffice_mail
    assert not office.members.exists()


@pytest.mark.django_db
def test_leave_mail_is_addressed_to_the_leaving_member(
    member, membership, logged_in_client, configuration
):
    Member.objects.create(email=member.email, number="2", name="Same Address")

    response = logged_in_client.post(
        reverse("office:members.operations", kwargs={"pk": member.pk}),
        {
            f"ms_{membership.pk}_leave-end": (now() + relativedelta(days=-1)).date(),
            f"submit_ms_{membership.pk}_leave_end": "end",
        },
    )

    assert response.status_code == 302, response.content.decode()
    config = Configuration.get_solo()
    leave = EMail.objects.get(template=config.leave_member_template)
    assert leave.to_type == RecipientType.MEMBER
    assert leave.get_member_recipients() == [member]
    office = EMail.objects.get(template=config.leave_office_template)
    assert office.to_type == RecipientType.ADDRESS
    assert office.to == config.backoffice_mail
    assert not office.members.exists()


@pytest.mark.django_db
def test_balance_reminders_are_addressed_to_their_members(
    member, membership, logged_in_client, configuration
):
    same_address = Member.objects.create(
        email=member.email, number="2", name="Same Address"
    )
    Membership.objects.create(
        member=same_address,
        start=membership.start,
        amount=20,
        interval=FeeIntervals.MONTHLY,
    )

    response = logged_in_client.post(
        reverse("office:members.balance"),
        {
            "start": str((now() - relativedelta(months=2)).date()),
            "end": str((now() - relativedelta(days=1)).date()),
            "create_if_zero": "on",
            "subject": "Your balance",
            "text": "Hello {name}",
        },
    )

    assert response.status_code == 302, response.content.decode()
    reminders = EMail.objects.filter(balance__isnull=False)
    assert reminders.count() == 2
    for reminder in reminders:
        assert reminder.to_type == RecipientType.MEMBER
        assert reminder.to == ""
        assert reminder.get_member_recipients() == [reminder.balance.member]
        assert reminder.text == f"Hello {reminder.balance.member.name}"
    # balances protect their member, which the member fixture deletes
    MemberBalance.objects.all().delete()


@pytest.mark.django_db
def test_data_disclosure_mails_are_addressed_to_their_members(
    member, membership, logged_in_client, configuration
):
    response = logged_in_client.post(
        reverse("office:members.record-disclosure", kwargs={"pk": member.pk})
    )

    assert response.status_code == 302, response.content.decode()
    mail = EMail.objects.get()
    assert mail.to_type == RecipientType.MEMBER
    assert mail.get_member_recipients() == [member]

    response = logged_in_client.post(reverse("office:members.disclosure"))

    assert response.status_code == 302, response.content.decode()
    assert EMail.objects.count() == 2
    for mail in EMail.objects.all():
        assert mail.to_type == RecipientType.MEMBER
        assert mail.get_member_recipients() == [member]


# -- the member selection never falls back to another member -----------------


@pytest.fixture
def external_contact(configuration):
    return Member.all_objects.create(
        email="contact@example.org",
        name="External Contact",
        membership_type=MemberTypes.EXTERNAL,
    )


@pytest.mark.django_db
def test_compose_link_works_for_an_external_contact(
    member, external_contact, logged_in_client, mailoutbox
):
    response = logged_in_client.get(
        reverse("office:members.mails", kwargs={"pk": external_contact.pk})
    )
    link = (
        f"{reverse('office:mails.compose')}"
        f"?to_type=member&amp;to_member={external_contact.pk}"
    )
    assert link in response.content.decode()
    url = link.replace("&amp;", "&")

    content = logged_in_client.get(url).content.decode()

    assert checked_recipient_type(content) == "member"
    assert selected_member(content) == external_contact.pk
    assert NO_MEMBER_WARNING not in content

    response = logged_in_client.post(
        url,
        compose_data(to_type="member", to_member=external_contact.pk, action="send"),
    )

    assert response.status_code == 302, response.content.decode()
    mail = EMail.objects.get()
    assert mail.sent is not None
    assert mail.get_member_recipients() == [external_contact]
    assert [message.to for message in mailoutbox] == [["contact@example.org"]]
    assert list(external_contact.emails.all()) == [mail]
    assert not member.emails.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query",
    (
        "to_type=member&to_member=999999",
        "to_type=member&to_member=abc",
        "to_type=member&to_member=",
        "to_type=member",
        "to_type=member&to_member={without_address}",
    ),
)
def test_compose_link_with_an_invalid_member_selects_nobody(
    member, logged_in_client, configuration, query
):
    without_address = Member.objects.create(number="20", name="No Address", email="")
    query = query.format(without_address=without_address.pk)

    response = logged_in_client.get(f"{reverse('office:mails.compose')}?{query}")
    content = response.content.decode()

    assert response.status_code == 200
    assert checked_recipient_type(content) == "member"
    # ``member`` is the first member of the list and must not be selected
    assert f'<option value="{member.pk}">' in content
    assert selected_member(content) is None
    assert NO_MEMBER_WARNING in content


@pytest.mark.django_db
def test_compose_for_a_valid_member_shows_no_warning(
    member, logged_in_client, configuration
):
    Member.objects.create(email="first@example.org", number="0", name="AAA First")

    response = logged_in_client.get(
        f"{reverse('office:mails.compose')}?to_type=member&to_member={member.pk}"
    )
    content = response.content.decode()

    assert selected_member(content) == member.pk
    assert NO_MEMBER_WARNING not in content


@pytest.mark.django_db
def test_compose_for_an_address_selects_no_member(
    member, logged_in_client, configuration
):
    response = logged_in_client.get(reverse("office:mails.compose"))
    content = response.content.decode()

    assert selected_member(content) is None
    assert NO_MEMBER_WARNING not in content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "to_member", ("999999", "abc", "", None, "{without_address}", "-1")
)
@pytest.mark.parametrize("action", ("save", "send"))
def test_compose_rejects_a_manipulated_member(
    member, logged_in_client, configuration, mailoutbox, to_member, action
):
    without_address = Member.objects.create(number="20", name="No Address", email="")
    data = compose_data(to_type="member", action=action)
    if to_member is not None:
        data["to_member"] = to_member.format(without_address=without_address.pk)

    response = logged_in_client.post(reverse("office:mails.compose"), data)
    content = response.content.decode()

    assert response.status_code == 200
    assert not EMail.objects.exists()
    assert len(mailoutbox) == 0
    assert not member.emails.exists()
    # the form comes back with an error and without a preselected member
    assert "invalid-feedback" in content
    assert selected_member(content) is None


@pytest.mark.django_db
def test_member_draft_without_a_member_selects_nobody(
    member, logged_in_client, configuration, mailoutbox
):
    mail = EMail.objects.create(
        to_type=RecipientType.MEMBER, subject="Test", text="Text"
    )
    url = reverse("office:mails.mail.view", kwargs={"pk": mail.pk})

    content = logged_in_client.get(url).content.decode()

    assert checked_recipient_type(content) == "member"
    assert selected_member(content) is None
    assert NO_MEMBER_WARNING in content

    # saving or sending what the browser shows does not pick a member
    response = logged_in_client.post(
        url, compose_data(to_type="member", to_member="", action="send")
    )

    assert response.status_code == 200
    mail.refresh_from_db()
    assert mail.sent is None
    assert mail.subject == "Test"
    assert not mail.members.exists()
    assert len(mailoutbox) == 0

    # and the outbox refuses to send it
    response = logged_in_client.get(
        reverse("office:mails.mail.send", kwargs={"pk": mail.pk}), follow=True
    )
    assert "no member is set as its recipient" in response.content.decode()
    assert len(mailoutbox) == 0

    # selecting a member explicitly repairs the draft
    response = logged_in_client.post(
        url, compose_data(to_type="member", to_member=member.pk, action="send")
    )
    assert response.status_code == 302, response.content.decode()
    assert [message.to for message in mailoutbox] == [[member.email]]


@pytest.mark.django_db
def test_member_draft_whose_member_was_deleted_selects_nobody(family, logged_in_client):
    member_a, member_b = family
    mail = member_mail(member_b)
    member_b.delete()

    content = logged_in_client.get(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk})
    ).content.decode()

    assert checked_recipient_type(content) == "member"
    assert selected_member(content) is None
    assert NO_MEMBER_WARNING in content


@pytest.mark.django_db
def test_member_draft_cannot_be_changed_to_an_invalid_member(family, logged_in_client):
    member_a, member_b = family
    mail = member_mail(member_b)

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(to_type="member", to_member="999999"),
    )

    assert response.status_code == 200
    mail.refresh_from_db()
    assert mail.subject == "Test"
    assert mail.get_member_recipients() == [member_b]


# -- recipients cannot be changed after a delivery ---------------------------


def send_failing_for(failing_member, mail):
    """Send ``mail``, but let the delivery to ``failing_member`` fail."""

    def fail(*args, member=None, **kwargs):
        if member == failing_member:
            raise SendMailException(f"{failing_member.name} cannot be reached.")
        return mail_send_task(*args, member=member, **kwargs)

    with patch("byro.mails.send.mail_send_task", side_effect=fail):
        with pytest.raises(SendMailException):
            mail.send()
    mail.refresh_from_db()


def activate(member):
    return Membership.objects.create(
        member=member,
        start=now().date() - relativedelta(months=1),
        amount=20,
        interval=FeeIntervals.MONTHLY,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data",
    (
        {"to_type": "member", "to_member": "{member_b}"},
        {"to_type": "addr", "to": "other@example.org"},
    ),
)
def test_partly_delivered_mail_keeps_its_recipients_and_history(
    family, logged_in_client, mailoutbox, data
):
    member_a, member_b = family
    activate(member_a)
    activate(member_b)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    send_failing_for(member_b, mail)
    assert mail.sent is None
    assert mail.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert list(member_a.emails.all()) == [mail]
    url = reverse("office:mails.mail.view", kwargs={"pk": mail.pk})

    # the form says so and offers a copy instead of a recipient selection
    content = logged_in_client.get(url).content.decode()
    assert "its recipients cannot be changed anymore" in content
    assert "<span" in content and "All members</span>" in content
    assert 'name="to_type"' not in content
    assert reverse("office:mails.mail.copy", kwargs={"pk": mail.pk}) in content

    # an attempt to change the recipients anyway is ignored
    data = {key: value.format(member_b=member_b.pk) for key, value in data.items()}
    response = logged_in_client.post(url, compose_data(**data))

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.subject == "Subject"
    assert mail.to_type == RecipientType.ALL_MEMBERS
    assert mail.to == ""
    assert mail.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert list(member_a.emails.all()) == [mail]
    assert not member_b.emails.exists()

    # the retry reaches the member that is still missing, and only that one
    response = logged_in_client.get(
        reverse("office:mails.mail.send", kwargs={"pk": mail.pk})
    )

    mail.refresh_from_db()
    assert mail.sent is not None
    assert len(mailoutbox) == 2
    assert member_b.profile_memberpage.get_url() in mailoutbox[1].body
    assert mail.delivered_to_members == {
        str(member_a.pk): SHARED_ADDRESS,
        str(member_b.pk): SHARED_ADDRESS,
    }
    assert list(member_a.emails.all()) == [mail]
    assert list(member_b.emails.all()) == [mail]


@pytest.mark.django_db
def test_partly_delivered_address_mail_keeps_its_recipients(
    family, logged_in_client, mailoutbox
):
    member_a, member_b = family
    mail = EMail.objects.create(
        to="one@example.org, two@example.org", subject="Test", text="Text"
    )

    def fail(*args, to=None, **kwargs):
        if to == ["two@example.org"]:
            raise SendMailException("two@example.org cannot be reached.")
        return mail_send_task(*args, to=to, **kwargs)

    with patch("byro.mails.send.mail_send_task", side_effect=fail):
        with pytest.raises(SendMailException):
            mail.send()

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(to_type="member", to_member=member_b.pk),
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.to_type == RecipientType.ADDRESS
    assert mail.to == "one@example.org, two@example.org"
    assert mail.delivered_to == ["one@example.org"]
    assert not mail.members.exists()

    mail.send()
    assert [message.to for message in mailoutbox] == [
        ["one@example.org"],
        ["two@example.org"],
    ]


@pytest.mark.django_db
def test_copy_of_a_partly_delivered_mail_can_get_other_recipients(
    family, logged_in_client, mailoutbox
):
    member_a, member_b = family
    activate(member_a)
    activate(member_b)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    send_failing_for(member_b, mail)

    logged_in_client.get(reverse("office:mails.mail.copy", kwargs={"pk": mail.pk}))
    copy = EMail.objects.exclude(pk=mail.pk).get()
    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": copy.pk}),
        compose_data(to_type="member", to_member=member_b.pk, action="send"),
    )

    assert response.status_code == 302, response.content.decode()
    copy.refresh_from_db()
    assert copy.sent is not None
    assert copy.delivered_to_members == {str(member_b.pk): SHARED_ADDRESS}
    assert copy.get_member_recipients() == [member_b]
    # the original keeps the record of its delivery
    mail.refresh_from_db()
    assert mail.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert set(member_a.emails.all()) == {mail}
    assert set(member_b.emails.all()) == {copy}


# -- the address a mail was delivered to ---------------------------------------


@pytest.mark.django_db
def test_sent_member_mail_shows_the_address_it_was_delivered_to(
    member, logged_in_client, configuration, mailoutbox
):
    member.email = "old@example.org"
    member.save()
    sent = member_mail(member, subject="Sent mail")
    sent.send()
    member_mail(member, subject="Draft mail")
    member.email = "new@example.org"
    member.save()

    for url in (
        reverse("office:mails.sent"),
        reverse("office:mails.mail.view", kwargs={"pk": sent.pk}),
        reverse("office:members.timeline", kwargs={"pk": member.pk}),
    ):
        content = logged_in_client.get(url).content.decode()
        assert "Jona Than &lt;old@example.org&gt;" in content, url
        assert "new@example.org" not in content, url

    # a draft goes to the address the member has now
    content = logged_in_client.get(reverse("office:mails.outbox.list")).content.decode()
    assert "<td>Jona Than &lt;new@example.org&gt;</td>" in content
    assert "old@example.org" not in content

    # the member's own list has both
    content = logged_in_client.get(
        reverse("office:members.mails", kwargs={"pk": member.pk})
    ).content.decode()
    assert "<td>Jona Than &lt;old@example.org&gt;</td>" in content
    assert "<td>Jona Than &lt;new@example.org&gt;</td>" in content


# -- reviewing a draft of an older version ---------------------------------------


def legacy_draft(to, *members, delivered_to=None):
    """A draft as an older version left it: the recipient encoded in ``to``,
    and members that were set before anything was sent."""
    mail = EMail.objects.create(to=to, subject="Legacy mail", text="Text")
    mail.members.add(*members)
    if delivered_to:
        # (set afterwards, as the members of a delivered mail are protected)
        EMail.objects.filter(pk=mail.pk).update(delivered_to=delivered_to)
        mail.refresh_from_db()
    return mail


def assert_not_in_history(client, member, subject="Legacy mail"):
    # an unrelated mail of the member: the timeline needs an entry to render
    member_mail(member, subject="Unrelated mail", sent=now())
    for url_name in ("office:members.mails", "office:members.timeline"):
        response = client.get(reverse(url_name, kwargs={"pk": member.pk}))
        content = response.content.decode()
        assert response.status_code == 200
        assert "Unrelated mail" in content, url_name
        assert subject not in content, url_name


@pytest.mark.django_db
def test_review_to_all_members_drops_stale_members(
    family, logged_in_client, mailoutbox
):
    """A was the member of an old balance reminder that was changed to "all
    members" and never sent. A is not active anymore, only B is."""
    member_a, member_b = family
    activate(member_b)
    mail = legacy_draft("special:all", member_a)
    assert list(member_a.emails.all()) == [mail]

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(to_type="all", subject="Legacy mail", action="send"),
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.sent is not None
    assert len(mailoutbox) == 1
    assert member_b.profile_memberpage.get_url() in mailoutbox[0].body
    assert mail.delivered_to_members == {str(member_b.pk): SHARED_ADDRESS}
    # only the member the mail was sent to has it in the history
    assert list(mail.members.all()) == [member_b]
    assert not member_a.emails.exists()
    assert_not_in_history(logged_in_client, member_a)
    content = logged_in_client.get(
        reverse("office:members.mails", kwargs={"pk": member_b.pk})
    ).content.decode()
    assert "Legacy mail" in content


@pytest.mark.django_db
def test_review_to_all_members_drops_stale_members_before_sending(
    family, logged_in_client
):
    member_a, member_b = family
    mail = legacy_draft("special:all", member_a)

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(to_type="all", subject="Legacy mail"),
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.to_type == RecipientType.ALL_MEMBERS
    assert mail.to == ""
    assert not mail.members.exists()
    assert_not_in_history(logged_in_client, member_a)


@pytest.mark.django_db
@pytest.mark.parametrize("to", ("special:all", "special:member:999999"))
def test_review_to_a_member_keeps_only_the_selected_member(
    family, logged_in_client, mailoutbox, to
):
    member_a, member_b = family
    mail = legacy_draft(to, member_a)

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(
            to_type="member",
            to_member=member_b.pk,
            subject="Legacy mail",
            action="send",
        ),
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.sent is not None
    assert mail.get_member_recipients() == [member_b]
    assert mail.delivered_to_members == {str(member_b.pk): SHARED_ADDRESS}
    assert member_b.profile_memberpage.get_url() in mailoutbox[0].body
    assert not member_a.emails.exists()
    assert_not_in_history(logged_in_client, member_a)


@pytest.mark.django_db
def test_review_to_an_address_drops_all_stale_members(
    family, logged_in_client, mailoutbox
):
    member_a, member_b = family
    mail = legacy_draft("special:all", member_a, member_b)

    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": mail.pk}),
        compose_data(
            to_type="addr", to=SHARED_ADDRESS, subject="Legacy mail", action="send"
        ),
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.sent is not None
    assert mail.to == SHARED_ADDRESS
    assert [message.body for message in mailoutbox] == ["Text"]
    assert not mail.members.exists()
    assert mail.delivered_to_members == {}
    assert_not_in_history(logged_in_client, member_a)
    assert_not_in_history(logged_in_client, member_b)


@pytest.mark.django_db
def test_changing_the_address_of_a_legacy_draft_drops_stale_members(
    family, logged_in_client
):
    member_a, member_b = family
    kept = legacy_draft("one@example.org", member_a)
    changed = legacy_draft("one@example.org", member_a)

    # the recipient is not selected anew, only the subject changes
    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": kept.pk}),
        compose_data(to_type="addr", to="one@example.org"),
    )
    assert response.status_code == 302, response.content.decode()
    response = logged_in_client.post(
        reverse("office:mails.mail.view", kwargs={"pk": changed.pk}),
        compose_data(to_type="addr", to="two@example.org"),
    )
    assert response.status_code == 302, response.content.decode()

    assert list(kept.members.all()) == [member_a]
    assert not changed.members.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data",
    (
        {"to_type": "all"},
        {"to_type": "member", "to_member": "{member_b}"},
        {"to_type": "addr", "to": "other@example.org"},
    ),
)
def test_review_with_a_delivery_stays_locked_and_keeps_the_history(
    family, logged_in_client, mailoutbox, data
):
    member_a, member_b = family
    activate(member_a)
    activate(member_b)
    mail = legacy_draft("special:all", member_a, delivered_to=[SHARED_ADDRESS])
    url = reverse("office:mails.mail.view", kwargs={"pk": mail.pk})

    content = logged_in_client.get(url).content.decode()
    assert "byro cannot tell which members have" in content
    assert 'name="to_type"' not in content

    data = {key: value.format(member_b=member_b.pk) for key, value in data.items()}
    response = logged_in_client.post(
        url, compose_data(subject="Legacy mail", action="send", **data)
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.sent is None
    assert mail.to_type == RecipientType.ADDRESS
    assert mail.to == "special:all"
    assert mail.delivered_to == [SHARED_ADDRESS]
    # the member that may have received the mail keeps it in the history
    assert list(mail.members.all()) == [member_a]
    assert list(member_a.emails.all()) == [mail]
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_recipient_change_is_refused_if_the_mail_was_delivered_meanwhile(
    family, logged_in_client
):
    """The delivery happens after the form was checked, before it is saved."""
    member_a, member_b = family
    mail = member_mail(member_a)
    url = reverse("office:mails.mail.view", kwargs={"pk": mail.pk})
    set_member_recipients = EMail.set_member_recipients

    def delivered_meanwhile(mail, members):
        EMail.objects.filter(pk=mail.pk).update(
            delivered_to=[SHARED_ADDRESS],
            delivered_to_members={str(member_a.pk): SHARED_ADDRESS},
        )
        return set_member_recipients(mail, members)

    with patch.object(EMail, "set_member_recipients", delivered_meanwhile):
        response = logged_in_client.post(
            url, compose_data(to_type="member", to_member=member_b.pk), follow=True
        )

    assert response.redirect_chain == [(url, 302)]
    assert "Its recipients cannot be changed anymore." in response.content.decode()
    mail.refresh_from_db()
    # nothing of the form was saved, not even the subject
    assert mail.subject == "Test"
    assert mail.get_member_recipients() == [member_a]
