import threading
import time
from unittest.mock import patch

import pytest
from dateutil.relativedelta import relativedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils.timezone import now

from byro.documents.models import Document
from byro.mails.models import EMail, RecipientsLockedError, RecipientType
from byro.mails.send import SendMailException, mail_send_task
from byro.members.models import FeeIntervals, Member, Membership, MemberTypes

SHARED_ADDRESS = "family@example.org"


def member_mail(*members, **kwargs):
    kwargs.setdefault("subject", "Test")
    kwargs.setdefault("text", "Text")
    mail = EMail.objects.create(to_type=RecipientType.MEMBER, **kwargs)
    mail.members.add(*members)
    return mail


def activate(member):
    return Membership.objects.create(
        member=member,
        start=now().date() - relativedelta(months=1),
        amount=20,
        interval=FeeIntervals.MONTHLY,
    )


def member_page_url(member):
    return member.profile_memberpage.get_url()


@pytest.fixture
def family(configuration):
    """Two members sharing one address."""
    return (
        Member.objects.create(email=SHARED_ADDRESS, number="10", name="Member A"),
        Member.objects.create(email=SHARED_ADDRESS, number="11", name="Member B"),
    )


@pytest.fixture
def send_task():
    """Record the calls of ``mail_send_task`` while still sending the mail."""
    with patch("byro.mails.send.mail_send_task", wraps=mail_send_task) as mock:
        yield mock


def sent_members(send_task):
    return [call.kwargs["member"] for call in send_task.call_args_list]


@pytest.mark.django_db
def test_member_mail_is_sent_to_the_address_of_the_member(
    member, configuration, send_task, mailoutbox
):
    mail = member_mail(member)

    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert [message.to for message in mailoutbox] == [[member.email]]
    assert sent_members(send_task) == [member]
    assert mail.to == ""
    assert mail.delivered_to == [member.email]
    assert mail.delivered_to_members == {str(member.pk): member.email}
    assert list(member.emails.all()) == [mail]


@pytest.mark.django_db
def test_member_mail_follows_a_changed_address(member, configuration, mailoutbox):
    mail = member_mail(member)
    member.email = "new@example.org"
    member.save()

    mail.send()

    assert mailoutbox[0].to == ["new@example.org"]


@pytest.mark.django_db
@pytest.mark.parametrize("addressed", (0, 1))
def test_shared_address_keeps_the_addressed_member(
    family, addressed, send_task, mailoutbox
):
    recipient, other = family[addressed], family[1 - addressed]
    mail = member_mail(recipient)

    mail.send()

    mail.refresh_from_db()
    assert sent_members(send_task) == [recipient]
    assert [message.to for message in mailoutbox] == [[SHARED_ADDRESS]]
    # the signature links to the member page of the addressed member
    assert member_page_url(recipient) in mailoutbox[0].body
    assert member_page_url(other) not in mailoutbox[0].body
    assert mail.delivered_to_members == {str(recipient.pk): SHARED_ADDRESS}
    assert list(recipient.emails.all()) == [mail]
    assert not other.emails.exists()


@pytest.mark.django_db
def test_mail_to_all_members_reaches_every_member_of_a_shared_address(
    family, send_task, mailoutbox
):
    member_a, member_b = family
    activate(member_a)
    activate(member_b)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )

    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert set(sent_members(send_task)) == {member_a, member_b}
    assert len(mailoutbox) == 2
    assert all(message.to == [SHARED_ADDRESS] for message in mailoutbox)
    bodies = {
        call.kwargs["member"]: call.kwargs["body"] for call in send_task.call_args_list
    }
    for recipient, other in ((member_a, member_b), (member_b, member_a)):
        assert member_page_url(recipient) in bodies[recipient]
        assert member_page_url(other) not in bodies[recipient]
    assert mail.delivered_to_members == {
        str(member_a.pk): SHARED_ADDRESS,
        str(member_b.pk): SHARED_ADDRESS,
    }
    assert mail.delivered_to == [SHARED_ADDRESS, SHARED_ADDRESS]
    assert list(member_a.emails.all()) == [mail]
    assert list(member_b.emails.all()) == [mail]


@pytest.mark.django_db
def test_mail_to_all_members_retries_only_the_member_that_failed(family, mailoutbox):
    member_a, member_b = family
    activate(member_a)
    activate(member_b)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )

    def fail_for_member_b(*args, member=None, **kwargs):
        if member == member_b:
            raise SendMailException("Member B cannot be reached.")
        return mail_send_task(*args, member=member, **kwargs)

    with patch("byro.mails.send.mail_send_task", side_effect=fail_for_member_b):
        with pytest.raises(SendMailException, match="Member B"):
            mail.send()

    mail.refresh_from_db()
    assert mail.sent is None
    # the shared address was delivered to, but only for member A
    assert mail.delivered_to == [SHARED_ADDRESS]
    assert mail.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert list(mail.members.all()) == [member_a]
    assert len(mailoutbox) == 1

    with patch("byro.mails.send.mail_send_task", wraps=mail_send_task) as send_task:
        mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert sent_members(send_task) == [member_b]
    assert mail.delivered_to_members == {
        str(member_a.pk): SHARED_ADDRESS,
        str(member_b.pk): SHARED_ADDRESS,
    }
    assert len(mailoutbox) == 2


@pytest.mark.django_db
def test_mail_to_all_members_only_reaches_active_members_with_an_address(
    member, membership, inactive_member, configuration, send_task
):
    without_address = Member.objects.create(number="20", name="No Address", email="")
    activate(without_address)
    # a second active membership must not lead to a second mail
    activate(member)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )

    mail.send()

    assert sent_members(send_task) == [member]


@pytest.mark.django_db
def test_specific_address_is_never_matched_to_a_member(
    member, configuration, send_task, mailoutbox
):
    mail = EMail.objects.create(to=member.email, subject="Test", text="Text")

    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert sent_members(send_task) == [None]
    assert mailoutbox[0].to == [member.email]
    assert mailoutbox[0].body == "Text"
    assert mail.delivered_to == [member.email]
    assert mail.delivered_to_members == {}
    assert not mail.members.exists()
    assert not member.emails.exists()


@pytest.mark.django_db
def test_specific_addresses_cc_bcc_reply_to_and_attachments_still_work(
    configuration, mailoutbox
):
    document = Document.objects.create(
        document=SimpleUploadedFile("testresource.txt", b"a resource"),
        title="Test document",
    )
    mail = EMail.objects.create(
        to="one@example.org, two@example.org",
        cc="cc@example.org",
        bcc="bcc@example.org",
        reply_to="reply@example.org",
        subject="Test",
        text="Text",
    )
    mail.attachments.add(document)

    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert [message.to for message in mailoutbox] == [
        ["one@example.org"],
        ["two@example.org"],
    ]
    for message in mailoutbox:
        assert message.cc == ["cc@example.org"]
        assert message.bcc == ["bcc@example.org"]
        assert message.extra_headers["Reply-To"] == "reply@example.org"
        assert len(message.attachments) == 1
    assert mail.delivered_to == ["one@example.org", "two@example.org"]
    document.delete()


@pytest.mark.django_db
def test_member_mail_without_an_address_is_not_sent(configuration, mailoutbox):
    member = Member.objects.create(number="20", name="No Address", email="")
    mail = member_mail(member)

    with pytest.raises(SendMailException, match="no email address"):
        mail.send()

    mail.refresh_from_db()
    assert mail.sent is None
    assert mail.delivered_to_members == {}
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_member_mail_without_a_member_is_not_sent(configuration, mailoutbox):
    mail = EMail.objects.create(
        to_type=RecipientType.MEMBER, subject="Test", text="Text"
    )

    with pytest.raises(SendMailException, match="no member"):
        mail.send()

    mail.refresh_from_db()
    assert mail.sent is None
    assert len(mailoutbox) == 0


@pytest.mark.django_db
@pytest.mark.parametrize("to", ("special:member:1", "special:all ", "special:other"))
def test_leftover_special_recipient_is_refused(member, configuration, mailoutbox, to):
    mail = EMail.objects.create(to=to, subject="Test", text="Text")

    with pytest.raises(SendMailException, match="has to be reviewed"):
        mail.send()

    mail.refresh_from_db()
    assert mail.sent is None
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_unknown_recipient_type_is_refused(member, membership, mailoutbox):
    mail = EMail.objects.create(to_type="other", subject="Test", text="Text")

    with pytest.raises(SendMailException, match="unknown recipient type"):
        mail.send()

    mail.refresh_from_db()
    assert mail.sent is None
    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_external_contact_can_be_a_member_recipient(configuration, send_task):
    contact = Member.all_objects.create(
        email="contact@example.org",
        name="External Contact",
        membership_type=MemberTypes.EXTERNAL,
    )
    mail = member_mail(contact)

    assert mail.get_member_recipients() == [contact]
    mail.send()

    assert sent_members(send_task) == [contact]


@pytest.mark.django_db
def test_set_member_recipients_replaces_all_members(family):
    member_a, member_b = family
    contact = Member.all_objects.create(
        email="contact@example.org",
        name="External Contact",
        membership_type=MemberTypes.EXTERNAL,
    )
    mail = member_mail(member_a, contact)

    mail.set_member_recipients([member_b])

    assert mail.get_member_recipients() == [member_b]


@pytest.mark.django_db
def test_copy_to_draft_keeps_member_recipients(family, mailoutbox):
    member_a, member_b = family
    mail = member_mail(member_a)
    mail.send()

    draft = mail.copy_to_draft()

    assert draft.pk != mail.pk
    assert draft.sent is None
    assert draft.to_type == RecipientType.MEMBER
    assert draft.get_member_recipients() == [member_a]
    assert draft.delivered_to == []
    assert draft.delivered_to_members == {}
    # the copy is an independent mail: sending it reaches the member again
    draft.send()
    assert len(mailoutbox) == 2
    assert draft.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    mail.refresh_from_db()
    assert mail.get_member_recipients() == [member_a]


@pytest.mark.django_db
def test_copy_to_draft_of_a_mail_to_all_members_does_not_copy_members(
    member, membership, configuration, mailoutbox
):
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    mail.send()
    assert list(mail.members.all()) == [member]

    draft = mail.copy_to_draft()

    assert draft.to_type == RecipientType.ALL_MEMBERS
    assert not draft.members.exists()
    assert draft.delivered_to_members == {}


@pytest.mark.django_db
def test_copy_to_draft_of_an_address_mail_does_not_copy_history_members(member):
    # a mail sent before the recipient type existed: the member was found by
    # the address back then and is not a recipient
    mail = EMail.objects.create(
        to=member.email, subject="Test", text="Text", sent=now()
    )
    mail.members.add(member)

    draft = mail.copy_to_draft()

    assert draft.to_type == RecipientType.ADDRESS
    assert draft.to == member.email
    assert not draft.members.exists()


@pytest.mark.django_db
def test_recipient_display(family):
    member_a, member_b = family

    assert EMail(to="one@example.org").recipient_display == "one@example.org"
    assert (
        str(EMail(to_type=RecipientType.ALL_MEMBERS).recipient_display) == "All members"
    )
    assert (
        member_mail(member_a, member_b).recipient_display
        == f"Member A <{SHARED_ADDRESS}>, Member B <{SHARED_ADDRESS}>"
    )


@pytest.mark.django_db
def test_recipient_display_can_be_prefetched(family, django_assert_num_queries):
    for member in family:
        member_mail(member)

    with django_assert_num_queries(2):
        displays = [
            mail.recipient_display
            for mail in EMail.objects.order_by("pk").with_member_recipients()
        ]

    assert displays == [
        f"Member A <{SHARED_ADDRESS}>",
        f"Member B <{SHARED_ADDRESS}>",
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("skip_queue", (True, False))
def test_template_to_mail_for_a_member(
    mail_template, member, configuration, send_task, skip_queue
):
    mail = mail_template.to_mail(member=member, skip_queue=skip_queue)

    mail.refresh_from_db()
    assert mail.to_type == RecipientType.MEMBER
    assert mail.to == ""
    assert mail.get_member_recipients() == [member]
    assert (mail.sent is None) is not skip_queue
    if not skip_queue:
        mail.send()
    assert sent_members(send_task) == [member]


@pytest.mark.django_db
def test_template_to_mail_unsaved_keeps_the_member(mail_template, member):
    mail = mail_template.to_mail(member=member, save=False)

    assert mail.pk is None
    assert mail.get_member_recipients() == [member]
    mail.save()

    assert EMail.objects.get(pk=mail.pk).get_member_recipients() == [member]


@pytest.mark.django_db
def test_template_to_mail_rejects_member_and_address(mail_template, member):
    with pytest.raises(ValueError):
        mail_template.to_mail("test@localhost", member=member)
    assert not EMail.objects.exists()


@pytest.mark.django_db
def test_template_to_mail_for_an_address_is_not_a_member_mail(mail_template, member):
    mail = mail_template.to_mail(member.email)

    assert mail.to_type == RecipientType.ADDRESS
    assert mail.to == member.email
    assert not mail.members.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("addressed", (0, 1))
def test_record_disclosure_mail_keeps_the_member(family, addressed, send_task):
    recipient = family[addressed]

    preview = recipient.record_disclosure_email
    assert preview.pk is None
    preview.save()

    mail = EMail.objects.get()
    assert mail.to_type == RecipientType.MEMBER
    assert mail.get_member_recipients() == [recipient]
    mail.send()
    assert sent_members(send_task) == [recipient]


@pytest.mark.django_db
@pytest.mark.parametrize("addressed", (0, 1))
def test_document_mail_keeps_the_member(family, addressed, send_task):
    recipient = family[addressed]
    document = Document.objects.create(
        document=SimpleUploadedFile("testresource.txt", b"a resource"),
        title="Test document",
        member=recipient,
    )

    mail = document.send(immediately=True)

    assert mail.to_type == RecipientType.MEMBER
    assert mail.get_member_recipients() == [recipient]
    assert sent_members(send_task) == [recipient]
    document.delete()


@pytest.mark.django_db
def test_document_mail_to_an_explicit_address_is_not_a_member_mail(
    member, configuration, send_task
):
    document = Document.objects.create(
        document=SimpleUploadedFile("testresource.txt", b"a resource"),
        title="Test document",
        member=member,
    )

    mail = document.send(immediately=True, email=member.email)

    assert mail.to_type == RecipientType.ADDRESS
    assert mail.to == member.email
    assert not mail.members.exists()
    assert sent_members(send_task) == [None]
    document.delete()


# -- storing a member mail together with its member --------------------------


@pytest.mark.django_db
def test_for_member_stores_the_mail_with_its_member(member, configuration, send_task):
    mail = EMail.for_member(member, subject="Test", text="Text")

    assert mail.pk is None
    assert mail.get_member_recipients() == [member]
    mail.save()
    # saving again neither loses nor duplicates the member
    mail.save()
    mail.save()

    mail = EMail.objects.get()
    assert mail.to_type == RecipientType.MEMBER
    assert mail.get_member_recipients() == [member]
    assert EMail.members.through.objects.count() == 1
    mail.send()
    assert sent_members(send_task) == [member]


@pytest.mark.django_db
def test_failed_first_save_does_not_lose_the_member(
    mail_template, member, configuration, send_task
):
    mail = mail_template.to_mail(member=member, save=False)

    with patch.object(
        EMail.members.related_manager_cls,
        "add",
        side_effect=RuntimeError("The member could not be stored."),
    ):
        with pytest.raises(RuntimeError):
            mail.save()

    # neither the mail nor a part of it was stored
    assert not EMail.objects.exists()
    assert mail.pk is None
    assert mail.get_member_recipients() == [member]

    mail.save()

    stored = EMail.objects.get()
    assert stored.pk == mail.pk
    assert stored.get_member_recipients() == [member]
    stored.send()
    assert sent_members(send_task) == [member]


@pytest.mark.django_db
def test_member_mail_changed_to_an_address_before_saving_drops_the_member(
    mail_template, member, configuration, send_task, mailoutbox
):
    mail = mail_template.to_mail(member=member, save=False)
    mail.to_type = RecipientType.ADDRESS
    mail.to = "outside@example.org"

    assert mail.get_member_recipients() == []
    mail.save()

    mail = EMail.objects.get()
    assert mail.to_type == RecipientType.ADDRESS
    assert not mail.members.exists()
    assert not member.emails.exists()
    mail.send()
    assert sent_members(send_task) == [None]
    assert [message.to for message in mailoutbox] == [["outside@example.org"]]
    assert member.profile_memberpage.get_url() not in mailoutbox[0].body


@pytest.mark.django_db
def test_member_mail_changed_to_all_members_before_saving_drops_the_member(
    mail_template, member, membership, configuration, send_task
):
    other = Member.objects.create(email="other@example.org", number="2", name="Other")
    mail = mail_template.to_mail(member=other, save=False)
    mail.to_type = RecipientType.ALL_MEMBERS

    mail.save()

    mail = EMail.objects.get()
    assert not mail.members.exists()
    # ``other`` has no active membership and is not a recipient anymore
    mail.send()
    assert sent_members(send_task) == [member]
    assert not other.emails.exists()


@pytest.mark.django_db
def test_dropped_member_does_not_come_back(mail_template, member, configuration):
    mail = mail_template.to_mail(member=member, save=False)
    mail.to_type = RecipientType.ADDRESS
    mail.to = "outside@example.org"
    mail.save()
    mail.to_type = RecipientType.MEMBER
    mail.to = ""
    mail.save()

    assert not mail.members.exists()
    with pytest.raises(SendMailException, match="no member"):
        mail.send()


# -- the record of deliveries -------------------------------------------------


@pytest.mark.django_db
def test_members_cannot_be_replaced_after_a_delivery(family, mailoutbox):
    member_a, member_b = family
    mail = member_mail(member_a, member_b)

    def fail_for_member_b(*args, member=None, **kwargs):
        if member == member_b:
            raise SendMailException("Member B cannot be reached.")
        return mail_send_task(*args, member=member, **kwargs)

    with patch("byro.mails.send.mail_send_task", side_effect=fail_for_member_b):
        with pytest.raises(SendMailException):
            mail.send()

    assert mail.has_deliveries
    with pytest.raises(ValueError):
        mail.set_member_recipients([member_b])
    assert mail.get_member_recipients() == [member_a, member_b]
    assert list(member_a.emails.all()) == [mail]


@pytest.mark.django_db
def test_retry_uses_the_current_address_and_keeps_the_delivered_one(
    configuration, mailoutbox
):
    member_a = Member.objects.create(email="a-old@example.org", number="10", name="A")
    member_b = Member.objects.create(email="b-old@example.org", number="11", name="B")
    mail = member_mail(member_a, member_b)
    assert mail.recipient_display == "A <a-old@example.org>, B <b-old@example.org>"

    def fail_for_member_b(*args, member=None, **kwargs):
        if member == member_b:
            raise SendMailException("Member B cannot be reached.")
        return mail_send_task(*args, member=member, **kwargs)

    with patch("byro.mails.send.mail_send_task", side_effect=fail_for_member_b):
        with pytest.raises(SendMailException):
            mail.send()

    # both members change their address before the retry
    for changed in (member_a, member_b):
        changed.email = changed.email.replace("old", "new")
        changed.save()
    mail = EMail.objects.get(pk=mail.pk)
    # A was reached at the old address, B will be reached at the new one
    assert mail.recipient_display == "A <a-old@example.org>, B <b-new@example.org>"

    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    # A is known as a member and is not sent to again at the new address
    assert [message.to for message in mailoutbox] == [
        ["a-old@example.org"],
        ["b-new@example.org"],
    ]
    assert mail.delivered_to_members == {
        str(member_a.pk): "a-old@example.org",
        str(member_b.pk): "b-new@example.org",
    }
    assert mail.recipient_display == "A <a-old@example.org>, B <b-new@example.org>"
    prefetched = EMail.objects.with_member_recipients().get(pk=mail.pk)
    assert prefetched.recipient_display == mail.recipient_display


@pytest.mark.django_db
def test_sent_mail_shows_the_delivered_address_for_each_member_of_a_shared_address(
    family, mailoutbox
):
    member_a, member_b = family
    mail = member_mail(member_a, member_b)
    mail.send()
    member_b.email = "b-new@example.org"
    member_b.save()

    mail = EMail.objects.get(pk=mail.pk)

    assert (
        mail.recipient_display
        == f"Member A <{SHARED_ADDRESS}>, Member B <{SHARED_ADDRESS}>"
    )
    # a new draft goes to the address of today
    assert (
        mail.copy_to_draft().recipient_display
        == f"Member A <{SHARED_ADDRESS}>, Member B <b-new@example.org>"
    )


@pytest.mark.django_db
def test_backend_error_keeps_the_recipients_that_were_reached(family, mailoutbox):
    """The mail server fails after the first member was delivered to."""
    from django.core.mail.backends.locmem import EmailBackend

    member_a, member_b = family
    member_b.email = "b@example.org"
    member_b.save()
    activate(member_a)
    activate(member_b)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    send_messages = EmailBackend.send_messages

    def connection_lost(backend, messages):
        if any(message.to == ["b@example.org"] for message in messages):
            raise OSError("Connection lost")
        return send_messages(backend, messages)

    with patch.object(EmailBackend, "send_messages", connection_lost):
        with pytest.raises(SendMailException, match="Failed to send"):
            mail.send()

    mail.refresh_from_db()
    assert mail.sent is None
    assert mail.delivered_to == [SHARED_ADDRESS]
    assert mail.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert list(member_a.emails.all()) == [mail]
    assert not member_b.emails.exists()
    assert [message.to for message in mailoutbox] == [[SHARED_ADDRESS]]

    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert [message.to for message in mailoutbox] == [
        [SHARED_ADDRESS],
        ["b@example.org"],
    ]
    assert list(member_b.emails.all()) == [mail]


# -- mail_send_task(member=...) ------------------------------------------------


@pytest.mark.django_db
def test_mail_send_task_with_a_member_takes_exactly_one_address(member, mailoutbox):
    mail_send_task(
        to=[member.email],
        cc=["cc@example.org"],
        subject="Test",
        body="Text",
        sender="sender@example.org",
        member=member,
    )

    assert [message.to for message in mailoutbox] == [[member.email]]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "to", (["joe@hacker.space", "outside@example.org"], [], [""], None)
)
def test_mail_send_task_with_a_member_refuses_other_numbers_of_addresses(
    member, mailoutbox, to
):
    with pytest.raises(SendMailException, match="exactly one address"):
        mail_send_task(
            to=to,
            cc=["cc@example.org"],
            subject="Test",
            body="Text",
            sender="sender@example.org",
            member=member,
        )

    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_mail_send_task_without_a_member_takes_several_addresses(mailoutbox):
    mail_send_task(
        to=["one@example.org", "two@example.org"],
        cc=["cc@example.org"],
        bcc=["bcc@example.org"],
        subject="Test",
        body="Text",
        sender="sender@example.org",
    )

    (message,) = mailoutbox
    assert message.to == ["one@example.org", "two@example.org"]
    assert message.cc == ["cc@example.org"]
    assert message.bcc == ["bcc@example.org"]


# -- recipients and deliveries are decided by the stored mail ---------------------


@pytest.fixture
def partly_delivered(family, mailoutbox):
    """A mail to all members that reached member A, but not member B.

    Returns the mail as it was loaded *before* that delivery, and both
    members. The stale object still believes that nothing was delivered."""
    member_a, member_b = family
    activate(member_a)
    activate(member_b)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    stale = EMail.objects.get(pk=mail.pk)

    def fail_for_member_b(*args, member=None, **kwargs):
        if member == member_b:
            raise SendMailException("Member B cannot be reached.")
        return mail_send_task(*args, member=member, **kwargs)

    with patch("byro.mails.send.mail_send_task", side_effect=fail_for_member_b):
        with pytest.raises(SendMailException):
            mail.send()

    assert not stale.has_deliveries
    assert stale.delivered_to == []
    assert stale.delivered_to_members == {}
    return stale, member_a, member_b


def stored(mail):
    return EMail.objects.get(pk=mail.pk)


def assert_delivery_to_member_a_is_intact(mail, member_a, member_b):
    mail = stored(mail)
    assert mail.sent is None
    assert mail.to_type == RecipientType.ALL_MEMBERS
    assert mail.to == ""
    assert mail.delivered_to == [SHARED_ADDRESS]
    assert mail.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert list(mail.members.all()) == [member_a]
    assert list(member_a.emails.all()) == [mail]
    assert not member_b.emails.exists()


@pytest.mark.django_db
def test_stale_object_cannot_replace_the_members_of_a_delivered_mail(partly_delivered):
    stale, member_a, member_b = partly_delivered

    with pytest.raises(RecipientsLockedError):
        stale.set_member_recipients([member_b])
    with pytest.raises(RecipientsLockedError):
        stale.set_member_recipients([])

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "change",
    (
        lambda mail, a, b: mail.members.remove(a),
        lambda mail, a, b: mail.members.clear(),
        lambda mail, a, b: mail.members.set([b]),
        lambda mail, a, b: mail.members.add(b),
        lambda mail, a, b: a.emails.remove(mail),
        lambda mail, a, b: a.emails.clear(),
        lambda mail, a, b: a.emails.set([]),
        lambda mail, a, b: b.emails.add(mail),
    ),
)
@pytest.mark.parametrize("use_stale_object", (True, False))
def test_members_relation_of_a_delivered_mail_cannot_be_changed(
    partly_delivered, change, use_stale_object
):
    stale, member_a, member_b = partly_delivered
    mail = stale if use_stale_object else stored(stale)

    # (the relation managers do not use a savepoint of their own, the block
    # lets the surrounding transaction of the test go on after the refusal)
    with pytest.raises(RecipientsLockedError), transaction.atomic():
        change(mail, member_a, member_b)

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "fields",
    (
        {"to_type": RecipientType.MEMBER},
        {"to_type": RecipientType.ADDRESS, "to": "other@example.org"},
        {"to": "other@example.org"},
    ),
)
@pytest.mark.parametrize("use_stale_object", (True, False))
@pytest.mark.parametrize("update_fields", (True, False))
def test_recipients_of_a_delivered_mail_cannot_be_saved(
    partly_delivered, fields, use_stale_object, update_fields
):
    stale, member_a, member_b = partly_delivered
    mail = stale if use_stale_object else stored(stale)
    for name, value in fields.items():
        setattr(mail, name, value)
    mail.subject = "Changed"

    with pytest.raises(RecipientsLockedError):
        if update_fields:
            mail.save(update_fields=[*fields, "subject"])
        else:
            mail.save()

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)
    # nothing of the refused save was stored
    assert stored(stale).subject == "Test"


@pytest.mark.django_db
def test_stale_save_does_not_reset_the_deliveries(partly_delivered, mailoutbox):
    stale, member_a, member_b = partly_delivered
    stale.subject = "Changed"

    stale.save()

    # the other fields are saved, the deliveries stay as they are stored ...
    assert stored(stale).subject == "Changed"
    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)
    # ... and the object knows them now
    assert stale.delivered_to == [SHARED_ADDRESS]
    assert stale.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}

    # so that sending again reaches member B only
    stale.send()

    assert [message.to for message in mailoutbox] == [
        [SHARED_ADDRESS],
        [SHARED_ADDRESS],
    ]
    assert member_b.profile_memberpage.get_url() in mailoutbox[1].body
    assert stored(stale).delivered_to_members == {
        str(member_a.pk): SHARED_ADDRESS,
        str(member_b.pk): SHARED_ADDRESS,
    }


@pytest.mark.django_db
def test_stale_save_cannot_wipe_deliveries_it_set_itself(partly_delivered):
    stale, member_a, member_b = partly_delivered
    stale.delivered_to = []
    stale.delivered_to_members = {}

    stale.save()

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)


@pytest.mark.django_db
def test_stale_object_does_not_send_to_a_delivered_member_again(
    partly_delivered, mailoutbox
):
    stale, member_a, member_b = partly_delivered

    stale.send()

    assert len(mailoutbox) == 2
    assert member_a.profile_memberpage.get_url() in mailoutbox[0].body
    assert member_b.profile_memberpage.get_url() in mailoutbox[1].body
    mail = stored(stale)
    assert mail.sent is not None
    assert mail.delivered_to == [SHARED_ADDRESS, SHARED_ADDRESS]
    assert set(mail.members.all()) == {member_a, member_b}


@pytest.mark.django_db
def test_stale_object_cannot_send_or_unsend_a_sent_mail(member, configuration):
    mail = EMail.for_member(member, subject="Test", text="Text")
    mail.save()
    stale = EMail.objects.get(pk=mail.pk)
    mail.send()

    with pytest.raises(TypeError):
        stale.send()

    stale = EMail.objects.get(pk=mail.pk)
    stale.sent = None
    stale.subject = "Changed"
    stale.save()

    mail = stored(mail)
    assert mail.subject == "Changed"
    assert mail.sent is not None
    assert mail.delivered_to_members == {str(member.pk): member.email}


@pytest.mark.django_db
def test_deliveries_recorded_by_two_objects_are_both_kept(family, mailoutbox):
    member_a, member_b = family
    mail = member_mail(member_a, member_b)
    other = EMail.objects.get(pk=mail.pk)

    mail._record_delivery(SHARED_ADDRESS, member_a)
    # ``other`` does not know the delivery to member A
    other._record_delivery("b@example.org", member_b)

    assert stored(mail).delivered_to == [SHARED_ADDRESS, "b@example.org"]
    assert stored(mail).delivered_to_members == {
        str(member_a.pk): SHARED_ADDRESS,
        str(member_b.pk): "b@example.org",
    }
    assert other.delivered_to_members == stored(mail).delivered_to_members


@pytest.mark.django_db
def test_other_fields_of_a_delivered_mail_can_still_be_saved(partly_delivered):
    stale, member_a, member_b = partly_delivered
    mail = stored(stale)
    mail.subject = "Changed"
    mail.text = "Changed text"

    mail.save()
    mail.save(update_fields=["subject"])

    assert stored(stale).text == "Changed text"
    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)


@pytest.mark.django_db
def test_recipients_can_be_changed_before_the_first_delivery(
    family, send_task, mailoutbox
):
    member_a, member_b = family
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    stale = EMail.objects.get(pk=mail.pk)

    # every way to change the recipients works, also on an older object
    mail.to_type = RecipientType.ADDRESS
    mail.to = "one@example.org"
    mail.save()
    assert (stored(mail).to_type, stored(mail).to) == ("addr", "one@example.org")
    stale.to_type = RecipientType.MEMBER
    stale.to = ""
    stale.save(update_fields=["to_type", "to"])
    stale.set_member_recipients([member_a])
    assert stored(mail).get_member_recipients() == [member_a]
    mail.members.add(member_b)
    mail.members.remove(member_a)
    member_a.emails.add(mail)
    member_b.emails.clear()
    mail.set_member_recipients([member_b])
    assert stored(mail).get_member_recipients() == [member_b]

    stored(mail).send()

    assert sent_members(send_task) == [member_b]
    assert stored(mail).delivered_to_members == {str(member_b.pk): SHARED_ADDRESS}


# -- concurrency, with a second database connection --------------------------------

needs_postgresql = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="needs row locks and a way to ask the database who waits for whom",
)

WAIT = 30


def replace_member(mail, member_b):
    mail.set_member_recipients([member_b])


def remove_members(mail, member_b):
    mail.set_member_recipients([])


def save_other_recipient(mail, member_b):
    mail.to_type = RecipientType.ADDRESS
    mail.to = "other@example.org"
    mail.save()


@needs_postgresql
@pytest.mark.parametrize(
    "change", (replace_member, remove_members, save_other_recipient)
)
@pytest.mark.django_db(transaction=True)
def test_recipient_change_waits_for_a_delivery_that_is_being_recorded(
    configuration, change
):
    """While a delivery to A is being recorded, another connection wants to
    change the recipients. It still sees a mail without deliveries, so it has
    to wait for the lock on the mail, and is refused once the delivery is
    stored."""
    member_a = Member.objects.create(email="a@example.org", number="10", name="A")
    member_b = Member.objects.create(email="b@example.org", number="11", name="B")
    mail = member_mail(member_a)
    stale = EMail.objects.get(pk=mail.pk)
    reached = threading.Event()
    other = {}

    def change_recipients():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                other["pid"] = cursor.fetchone()[0]
            reached.set()
            change(stale, member_b)
            other["changed"] = True
        except Exception as exc:
            other["error"] = exc
        finally:
            connection.close()

    thread = threading.Thread(target=change_recipients)
    with transaction.atomic():
        # the delivery is recorded, but not committed yet
        mail._record_delivery("a@example.org", member_a)
        thread.start()
        assert reached.wait(WAIT)
        blocked = False
        deadline = time.monotonic() + WAIT
        while not blocked and time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_backend_pid() = ANY(pg_blocking_pids(%s))",
                    [other["pid"]],
                )
                blocked = cursor.fetchone()[0]
            if not blocked:
                time.sleep(0.01)
        # the other connection waits for exactly this transaction
        assert blocked
        assert "changed" not in other and "error" not in other

    thread.join(timeout=WAIT)
    assert not thread.is_alive()
    assert isinstance(other.get("error"), RecipientsLockedError)
    assert "changed" not in other
    mail = EMail.objects.get(pk=mail.pk)
    assert (mail.to_type, mail.to) == (RecipientType.MEMBER, "")
    assert mail.get_member_recipients() == [member_a]
    assert mail.delivered_to_members == {str(member_a.pk): "a@example.org"}
    assert not member_b.emails.exists()


# -- save() is no way to change what was delivered ---------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "update_fields",
    (
        ["delivered_to"],
        ["delivered_to_members"],
        ["delivered_to", "delivered_to_members"],
        ["delivered_to", "delivered_to_members", "sent"],
        ["subject", "delivered_to", "delivered_to_members"],
        None,
    ),
)
def test_stale_save_with_update_fields_keeps_the_deliveries(
    partly_delivered, update_fields
):
    stale, member_a, member_b = partly_delivered
    assert stale.delivered_to == []
    assert stale.delivered_to_members == {}

    stale.save(update_fields=update_fields)

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)
    # the object has taken over what is stored
    assert stale.delivered_to == [SHARED_ADDRESS]
    assert stale.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}

    # values that are set on purpose are not stored either
    stale.delivered_to = []
    stale.delivered_to_members = {}
    stale.save(update_fields=update_fields)
    fresh = stored(stale)
    fresh.delivered_to = ["other@example.org"]
    fresh.delivered_to_members = {str(member_b.pk): "other@example.org"}
    fresh.save(update_fields=update_fields)

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)
    # so the recipients stay locked, for every object
    for mail in (stale, fresh, stored(stale)):
        with pytest.raises(RecipientsLockedError):
            mail.set_member_recipients([member_b])
    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "update_fields",
    (["sent"], ["sent", "delivered_to", "delivered_to_members"], None),
)
def test_stale_save_cannot_unsend_a_sent_mail(family, mailoutbox, update_fields):
    member_a, member_b = family
    mail = member_mail(member_a)
    stale = EMail.objects.get(pk=mail.pk)
    mail.send()
    sent = stored(mail).sent
    assert sent is not None
    assert stale.sent is None

    stale.save(update_fields=update_fields)

    assert stored(mail).sent == sent
    assert stale.sent == sent

    # neither can another time or "not sent" be set on purpose
    for value in (None, now() + relativedelta(days=1)):
        fresh = stored(mail)
        fresh.sent = value
        fresh.save(update_fields=update_fields)
        assert stored(mail).sent == sent

    assert stored(mail).delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    for other in (stale, stored(mail)):
        with pytest.raises(RecipientsLockedError):
            other.set_member_recipients([member_b])
        with pytest.raises(TypeError):
            other.send()
    assert stored(mail).get_member_recipients() == [member_a]
    assert len(mailoutbox) == 1


@pytest.mark.django_db
@pytest.mark.parametrize("update_fields", (["sent"], None))
def test_save_cannot_mark_a_stored_mail_as_sent(member, configuration, update_fields):
    mail = member_mail(member)
    mail.sent = now()

    mail.save(update_fields=update_fields)

    # only send() does that, after the mail was delivered
    assert stored(mail).sent is None
    assert mail.sent is None


@pytest.mark.django_db
def test_new_mail_can_be_created_with_its_delivery_state(member):
    # e.g. an import of mails that were sent elsewhere
    sent = now()
    mail = EMail.objects.create(
        to="one@example.org",
        subject="Test",
        text="Text",
        sent=sent,
        delivered_to=["one@example.org"],
    )

    assert stored(mail).sent == sent
    assert stored(mail).delivered_to == ["one@example.org"]


# -- send() works on the stored recipients ------------------------------------------


def fail_for(failing_member):
    def fail(*args, member=None, **kwargs):
        if member == failing_member:
            raise SendMailException(f"{failing_member.name} cannot be reached.")
        return mail_send_task(*args, member=member, **kwargs)

    return patch("byro.mails.send.mail_send_task", side_effect=fail)


@pytest.mark.django_db
def test_stale_address_object_sends_to_the_stored_member_recipients(family, mailoutbox):
    member_a, member_b = family
    mail = EMail.objects.create(to=SHARED_ADDRESS, subject="Test", text="Text")
    stale = EMail.objects.get(pk=mail.pk)
    # the draft is changed to the members A and B, who share that address
    mail.to_type = RecipientType.MEMBER
    mail.to = ""
    mail.save()
    mail.set_member_recipients([member_a, member_b])
    with fail_for(member_b), pytest.raises(SendMailException):
        mail.send()
    assert stored(mail).delivered_to == [SHARED_ADDRESS]
    assert stored(mail).delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    # the stale object still believes in a mail to the address
    assert (stale.to_type, stale.to) == (RecipientType.ADDRESS, SHARED_ADDRESS)

    # B fails once more: the mail must not be taken for sent
    with fail_for(member_b), pytest.raises(SendMailException, match="Member B"):
        stale.send()

    assert stored(mail).sent is None
    assert stored(mail).delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert len(mailoutbox) == 1
    stale = EMail.objects.get(pk=mail.pk)
    stale.to_type = RecipientType.ADDRESS
    stale.to = SHARED_ADDRESS

    with patch("byro.mails.send.mail_send_task", wraps=mail_send_task) as send_task:
        stale.send()

    # B was sent to as a member, A was not sent to again
    assert sent_members(send_task) == [member_b]
    assert len(mailoutbox) == 2
    assert member_b.profile_memberpage.get_url() in mailoutbox[1].body
    assert member_a.profile_memberpage.get_url() not in mailoutbox[1].body
    mail = stored(mail)
    assert mail.sent is not None
    assert mail.to_type == RecipientType.MEMBER
    assert mail.to == ""
    assert mail.delivered_to_members == {
        str(member_a.pk): SHARED_ADDRESS,
        str(member_b.pk): SHARED_ADDRESS,
    }
    assert list(member_b.emails.all()) == [mail]
    # the object knows the stored mail now
    assert (stale.to_type, stale.to) == (RecipientType.MEMBER, "")
    assert stale.sent == mail.sent


@pytest.mark.django_db
def test_stale_member_object_sends_to_the_stored_address(
    member, configuration, send_task, mailoutbox
):
    mail = member_mail(member)
    stale = EMail.objects.get(pk=mail.pk)
    mail.to_type = RecipientType.ADDRESS
    mail.to = "outside@example.org"
    mail.save()
    mail.set_member_recipients([])
    assert stale.to_type == RecipientType.MEMBER

    stale.send()

    # no member context for the address
    assert sent_members(send_task) == [None]
    assert [message.to for message in mailoutbox] == [["outside@example.org"]]
    assert mailoutbox[0].body == "Text"
    mail = stored(mail)
    assert mail.sent is not None
    assert mail.delivered_to == ["outside@example.org"]
    assert mail.delivered_to_members == {}
    assert not member.emails.exists()


@pytest.mark.django_db
def test_stale_member_object_sends_to_the_stored_member(family, send_task, mailoutbox):
    member_a, member_b = family
    mail = member_mail(member_a)
    stale = EMail.objects.get(pk=mail.pk)
    assert stale.get_member_recipients() == [member_a]
    mail.set_member_recipients([member_b])

    stale.send()

    assert sent_members(send_task) == [member_b]
    assert member_b.profile_memberpage.get_url() in mailoutbox[0].body
    assert member_a.profile_memberpage.get_url() not in mailoutbox[0].body
    assert stored(mail).delivered_to_members == {str(member_b.pk): SHARED_ADDRESS}
    assert not member_a.emails.exists()


@pytest.mark.django_db
def test_stale_prefetched_object_sends_to_the_stored_member(family, send_task):
    member_a, member_b = family
    mail = member_mail(member_a)
    stale = EMail.objects.with_member_recipients().get(pk=mail.pk)
    assert stale.get_member_recipients() == [member_a]
    mail.set_member_recipients([member_b])

    stale.send()

    assert sent_members(send_task) == [member_b]
    assert stale.get_member_recipients() == [member_b]
    assert stale.recipient_display == f"Member B <{SHARED_ADDRESS}>"


@pytest.mark.django_db
def test_send_ignores_recipients_that_were_not_saved(
    member, configuration, send_task, mailoutbox
):
    mail = EMail.objects.create(to="one@example.org", subject="Test", text="Text")
    mail.to = "two@example.org"

    mail.send()

    assert [message.to for message in mailoutbox] == [["one@example.org"]]
    assert mail.to == "one@example.org"


@pytest.mark.django_db
def test_unsaved_mail_cannot_be_sent(member, configuration, mailoutbox):
    mail = EMail(to="one@example.org", subject="Test", text="Text")

    with pytest.raises(ValueError):
        mail.send()

    assert len(mailoutbox) == 0


@pytest.mark.django_db
def test_mail_is_not_sent_while_a_stored_recipient_is_open(family, mailoutbox):
    """The recipients are extended by member B while member A is sent to."""
    member_a, member_b = family
    mail = member_mail(member_a)

    def add_member_b_meanwhile(*args, **kwargs):
        EMail.objects.get(pk=mail.pk).set_member_recipients([member_a, member_b])
        return mail_send_task(*args, **kwargs)

    with patch("byro.mails.send.mail_send_task", side_effect=add_member_b_meanwhile):
        with pytest.raises(SendMailException, match="were changed while it was sent"):
            mail.send()

    # A was delivered to, but the mail is not complete
    assert stored(mail).sent is None
    assert mail.sent is None
    assert stored(mail).delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert len(mailoutbox) == 1

    with patch("byro.mails.send.mail_send_task", wraps=mail_send_task) as send_task:
        mail.send()

    assert sent_members(send_task) == [member_b]
    assert stored(mail).sent is not None
    assert len(mailoutbox) == 2


@pytest.mark.django_db
def test_mail_to_all_members_is_not_sent_while_an_active_member_is_open(
    family, mailoutbox
):
    """Member B becomes an active member while member A is sent to."""
    member_a, member_b = family
    activate(member_a)
    mail = EMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )

    def activate_member_b_meanwhile(*args, **kwargs):
        activate(member_b)
        return mail_send_task(*args, **kwargs)

    with patch(
        "byro.mails.send.mail_send_task", side_effect=activate_member_b_meanwhile
    ):
        with pytest.raises(SendMailException, match="were changed while it was sent"):
            mail.send()

    assert stored(mail).sent is None
    assert list(mail.members.all()) == [member_a]

    mail.send()

    assert stored(mail).sent is not None
    assert len(mailoutbox) == 2
    assert member_b.profile_memberpage.get_url() in mailoutbox[1].body
    assert set(mail.members.all()) == {member_a, member_b}


@pytest.mark.django_db
def test_mail_that_somebody_else_finished_stays_sent(family, mailoutbox):
    """Another object sends the mail completely while this one is at it."""
    member_a, member_b = family
    mail = member_mail(member_a)
    sent = {}

    def send_by_another_object_meanwhile(*args, **kwargs):
        if not sent:
            sent["at"] = None
            other = EMail.objects.get(pk=mail.pk)
            other.send()
            sent["at"] = other.sent
        return mail_send_task(*args, **kwargs)

    with patch(
        "byro.mails.send.mail_send_task", side_effect=send_by_another_object_meanwhile
    ):
        mail.send()

    assert stored(mail).sent == sent["at"]
    assert mail.sent == sent["at"]
    with pytest.raises(TypeError):
        mail.send()


# -- an object that is built with the primary key of a stored mail ----------------


def rebuilt(mail, **fields):
    """A new object with the primary key of a stored mail. It was not loaded
    from the database: Django takes it for an object that is being added."""
    fields.setdefault("subject", mail.subject)
    fields.setdefault("text", mail.text)
    other = EMail(pk=mail.pk, **fields)
    assert other._state.adding
    assert other.delivered_to == []
    assert other.delivered_to_members == {}
    assert other.sent is None
    return other


def unused_pk():
    return (
        EMail.objects.order_by("-pk").values_list("pk", flat=True).first() or 0
    ) + 1000


@pytest.mark.django_db
@pytest.mark.parametrize(
    "update_fields",
    (
        ["delivered_to", "delivered_to_members", "sent"],
        ["delivered_to"],
        ["delivered_to_members"],
        ["sent"],
    ),
)
def test_rebuilt_object_cannot_wipe_the_deliveries(partly_delivered, update_fields):
    stale, member_a, member_b = partly_delivered
    other = rebuilt(stale, to_type=RecipientType.MEMBER)

    other.save(update_fields=update_fields)

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)
    # the object has taken over what is stored, and the recipients stay locked
    assert other.delivered_to == [SHARED_ADDRESS]
    assert other.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    for mail in (other, rebuilt(stale), stored(stale)):
        with pytest.raises(RecipientsLockedError):
            mail.set_member_recipients([member_b])
    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "fields",
    (
        {"to_type": RecipientType.MEMBER},
        {"to_type": RecipientType.ADDRESS, "to": "other@example.org"},
        {"to_type": RecipientType.ALL_MEMBERS, "to": "other@example.org"},
        # the default recipient type of a new object is "addr"
        {},
    ),
)
def test_rebuilt_object_cannot_change_the_recipients_of_a_delivered_mail(
    partly_delivered, fields
):
    stale, member_a, member_b = partly_delivered
    other = rebuilt(stale, subject="Changed", **fields)

    with pytest.raises(RecipientsLockedError):
        other.save()
    with pytest.raises(RecipientsLockedError):
        other.save(update_fields=["to_type", "to", "subject"])

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)
    assert stored(stale).subject == "Test"


@pytest.mark.django_db
def test_rebuilt_member_mail_cannot_add_a_member_to_a_delivered_mail(
    family, mailoutbox
):
    member_a, member_b = family
    mail = member_mail(member_a, member_b)
    with fail_for(member_b), pytest.raises(SendMailException):
        mail.send()
    other = EMail.for_member(member_b, pk=mail.pk, subject="Changed", text="Text")
    third = Member.objects.create(email="c@example.org", number="12", name="Member C")
    another = EMail.for_member(third, pk=mail.pk, subject="Changed", text="Text")

    # B is a member of the mail already, C is not
    other.save()
    with pytest.raises(RecipientsLockedError), transaction.atomic():
        another.save()

    mail = stored(mail)
    assert mail.subject == "Changed"
    assert mail.get_member_recipients() == [member_a, member_b]
    assert mail.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert not third.emails.exists()


@pytest.mark.django_db
def test_rebuilt_object_with_the_same_recipients_keeps_the_deliveries(
    partly_delivered, mailoutbox
):
    stale, member_a, member_b = partly_delivered
    other = rebuilt(stale, to_type=RecipientType.ALL_MEMBERS, subject="Changed")

    other.save()

    # the other fields are saved like those of any object
    assert stored(stale).subject == "Changed"
    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)
    assert not other._state.adding

    # and the mail still only misses member B
    other.send()

    assert len(mailoutbox) == 2
    assert member_b.profile_memberpage.get_url() in mailoutbox[1].body
    assert stored(stale).sent is not None


@pytest.mark.django_db
@pytest.mark.parametrize("update_fields", (None, ["sent"], ["sent", "subject"]))
@pytest.mark.parametrize("sent", (None, "another time"))
def test_rebuilt_object_cannot_unsend_a_sent_mail(
    family, mailoutbox, update_fields, sent
):
    member_a, member_b = family
    mail = member_mail(member_a)
    mail.send()
    sent_at = stored(mail).sent
    assert sent_at is not None
    other = rebuilt(mail, to_type=RecipientType.MEMBER, subject="Changed")
    if sent:
        other.sent = sent_at + relativedelta(days=1)

    other.save(update_fields=update_fields)

    mail = stored(mail)
    assert mail.sent == sent_at
    assert other.sent == sent_at
    # the fields that were to be saved besides are saved
    subject_saved = update_fields is None or "subject" in update_fields
    assert mail.subject == ("Changed" if subject_saved else "Test")
    assert mail.delivered_to == [SHARED_ADDRESS]
    assert mail.delivered_to_members == {str(member_a.pk): SHARED_ADDRESS}
    assert mail.get_member_recipients() == [member_a]
    # it is not sent again, and its member stays
    for sent_mail in (other, mail):
        with pytest.raises(TypeError):
            sent_mail.send()
        with pytest.raises(RecipientsLockedError):
            sent_mail.set_member_recipients([member_b])
    assert len(mailoutbox) == 1
    assert list(member_a.emails.all()) == [mail]


@pytest.mark.django_db
def test_rebuilt_object_can_change_a_mail_that_was_not_delivered(member, send_task):
    mail = EMail.objects.create(to="one@example.org", subject="Test", text="Text")
    other = EMail.for_member(member, pk=mail.pk, subject="Changed", text="Text")

    other.save()

    assert EMail.objects.count() == 1
    mail = stored(mail)
    assert (mail.to_type, mail.to, mail.subject) == ("member", "", "Changed")
    assert mail.get_member_recipients() == [member]
    mail.send()
    assert sent_members(send_task) == [member]


@pytest.mark.django_db
def test_new_mail_without_a_primary_key_is_created(member, configuration):
    mail = EMail(to="one@example.org", subject="Test", text="Text", sent=now())
    mail.save()
    member_mail_ = EMail.for_member(member, subject="Test", text="Text")
    member_mail_.save()

    assert EMail.objects.count() == 2
    assert stored(mail).sent is not None
    assert stored(member_mail_).get_member_recipients() == [member]


@pytest.mark.django_db
def test_new_mail_with_an_unused_primary_key_is_created(member, configuration):
    EMail.objects.create(to="existing@example.org", subject="Test", text="Text")
    sent = now()
    pk = unused_pk()
    mail = EMail(
        pk=pk,
        to="one@example.org",
        subject="Test",
        text="Text",
        sent=sent,
        delivered_to=["one@example.org"],
    )

    mail.save()

    # a new mail may bring its delivery state along
    assert not mail._state.adding
    assert EMail.objects.count() == 2
    assert stored(mail).pk == pk
    assert stored(mail).sent == sent
    assert stored(mail).delivered_to == ["one@example.org"]

    member_mail_ = EMail.for_member(member, pk=pk + 1, subject="Test", text="Text")
    member_mail_.save()
    created = EMail.objects.create(pk=pk + 2, to="x@example.org", subject="T", text="T")

    assert stored(member_mail_).get_member_recipients() == [member]
    assert stored(created).pk == pk + 2
    assert EMail.objects.count() == 4


@pytest.mark.django_db
def test_object_of_a_deleted_mail_is_created_again(configuration):
    mail = EMail.objects.create(to="one@example.org", subject="Test", text="Text")
    pk = mail.pk
    EMail.objects.filter(pk=pk).delete()

    mail.save()

    assert stored(mail).pk == pk


@pytest.mark.django_db
def test_nothing_is_updated_under_an_unused_primary_key(configuration):
    mail = EMail(pk=unused_pk(), to="one@example.org", subject="Test", text="Text")

    with pytest.raises(DatabaseError):
        mail.save(update_fields=["subject"])
    with pytest.raises(DatabaseError):
        mail.save(force_update=True)
    # Django saves nothing for an empty list of fields
    mail.save(update_fields=[])

    assert not EMail.objects.exists()


@pytest.mark.django_db
def test_stored_mail_cannot_be_replaced_by_an_insert(partly_delivered):
    stale, member_a, member_b = partly_delivered

    with pytest.raises(IntegrityError), transaction.atomic():
        EMail.objects.create(pk=stale.pk, to="x@example.org", subject="T", text="T")
    with pytest.raises(IntegrityError), transaction.atomic():
        rebuilt(stale).save(force_insert=True)

    assert_delivery_to_member_a_is_intact(stale, member_a, member_b)
