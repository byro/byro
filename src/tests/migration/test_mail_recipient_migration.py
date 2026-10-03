import importlib

import pytest
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.shortcuts import reverse as reverse_url
from django.utils.timezone import now

from byro.mails.models import EMail as CurrentEMail
from byro.mails.models import RecipientType
from byro.mails.send import SendMailException, mail_send_task
from byro.members.models import FeeIntervals
from byro.members.models import Member as CurrentMember
from byro.members.models import MemberBalance as CurrentMemberBalance
from byro.members.models import Membership

MIGRATION = ("mails", "0012_migrate_special_recipients")
BEFORE = ("mails", "0010_email_delivered_to")

migration_module = importlib.import_module(
    "byro.mails.migrations.0012_migrate_special_recipients"
)


@pytest.fixture
def historical_apps():
    """The historical models the data migration receives during ``migrate``.
    The SQLite schema editor cannot run inside the transaction of a test, so
    the migration executor itself is not used here."""
    return MigrationLoader(connection).project_state(MIGRATION).apps


@pytest.fixture
def models(historical_apps):
    return (
        historical_apps.get_model("mails", "EMail"),
        historical_apps.get_model("members", "Member"),
        historical_apps.get_model("members", "MemberBalance"),
    )


@pytest.fixture
def migrate(historical_apps):
    def run():
        migration_module.migrate_special_recipients(historical_apps, None)

    return run


@pytest.fixture
def reverse(historical_apps):
    def run():
        migration_module.restore_special_recipients(historical_apps, None)

    return run


def old_mail(EMail, to, **kwargs):
    """A mail as the code before ``to_type`` stored it."""
    return EMail.objects.create(to=to, subject="Test", text="Text", **kwargs)


def state(mail):
    mail.refresh_from_db()
    return (
        mail.to_type,
        mail.to,
        sorted(mail.members.values_list("pk", flat=True)),
        mail.delivered_to_members,
    )


def activate(member):
    Membership.objects.create(
        member_id=member.pk,
        start=now().date() - relativedelta(months=1),
        amount=20,
        interval=FeeIntervals.MONTHLY,
    )


@pytest.fixture
def cleanup_balances():
    # balances protect their member
    yield
    CurrentMemberBalance.objects.all().delete()


@pytest.mark.django_db
def test_special_member_draft_becomes_a_member_mail(models, migrate):
    EMail, Member, MemberBalance = models
    # both members share one address, the primary key tells them apart
    member_a = Member.objects.create(email="family@example.org", name="A")
    member_b = Member.objects.create(email="family@example.org", name="B")
    mail_a = old_mail(EMail, f"special:member:{member_a.pk}")
    mail_b = old_mail(EMail, f"special:member:{member_b.pk}")

    migrate()

    assert state(mail_a) == ("member", "", [member_a.pk], {})
    assert state(mail_b) == ("member", "", [member_b.pk], {})


@pytest.mark.django_db
@pytest.mark.parametrize(
    "to", ("special:member:999999", "special:member:", "special:member:abc")
)
def test_special_member_draft_without_a_member_is_left_alone(models, migrate, to):
    EMail, Member, MemberBalance = models
    Member.objects.create(email="member@example.org", name="A")
    mail = old_mail(EMail, to)

    migrate()

    assert state(mail) == ("addr", to, [], {})


@pytest.mark.django_db
def test_special_member_draft_with_traces_of_a_delivery_is_left_alone(models, migrate):
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="a@example.org", name="A")
    member_b = Member.objects.create(email="b@example.org", name="B")
    to = f"special:member:{member_b.pk}"
    # an address draft that reached A and was then changed to member B
    delivered = old_mail(EMail, to, delivered_to=["a@example.org"])
    delivered.members.add(member_a)
    # the same before deliveries were recorded: only the member tells
    other_member = old_mail(EMail, to)
    other_member.members.add(member_a)

    migrate()

    assert state(delivered) == ("addr", to, [member_a.pk], {})
    assert delivered.delivered_to == ["a@example.org"]
    assert state(other_member) == ("addr", to, [member_a.pk], {})


@pytest.mark.django_db
def test_unsent_mail_to_all_members_becomes_a_recipient_type(models, migrate):
    EMail, Member, MemberBalance = models
    Member.objects.create(email="family@example.org", name="A")
    draft = old_mail(EMail, "special:all")

    migrate()

    assert state(draft) == ("all", "", [], {})
    assert draft.sent is None


@pytest.mark.django_db
def test_sent_mail_to_all_members_becomes_a_recipient_type(models, migrate):
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="family@example.org", name="A")
    member_b = Member.objects.create(email="family@example.org", name="B")
    sent = old_mail(
        EMail,
        "special:all",
        sent=now(),
        delivered_to=["family@example.org", "other@example.org"],
    )
    sent.members.add(member_a, member_b)

    migrate()

    # the members stay as the history of the mail, but they are not turned
    # into a record of deliveries
    assert state(sent) == ("all", "", sorted([member_a.pk, member_b.pk]), {})
    assert sent.sent is not None
    assert sent.delivered_to == ["family@example.org", "other@example.org"]


@pytest.mark.django_db
def test_partly_delivered_mail_to_all_members_is_left_for_review(models, migrate):
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="family@example.org", name="A")
    Member.objects.create(email="family@example.org", name="B")
    # the first member was reached, then the send failed
    unfinished = old_mail(EMail, "special:all", delivered_to=["family@example.org"])
    unfinished.members.add(member_a)
    # the same before deliveries were recorded
    unfinished_old = old_mail(EMail, "special:all")
    unfinished_old.members.add(member_a)

    migrate()

    assert state(unfinished) == ("addr", "special:all", [member_a.pk], {})
    assert unfinished.delivered_to == ["family@example.org"]
    assert state(unfinished_old) == ("addr", "special:all", [member_a.pk], {})


@pytest.mark.django_db
def test_members_of_a_mail_to_all_members_are_no_delivery_evidence(
    models, migrate, cleanup_balances, logged_in_client, configuration, mailoutbox
):
    """A balance reminder for A is changed to "all members" before sending.
    A was never delivered to and must not be skipped after the migration."""
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="a@example.org", name="A")
    member_b = Member.objects.create(email="b@example.org", name="B")
    activate(member_a)
    activate(member_b)
    balance = MemberBalance.objects.create(
        member=member_a, amount=-10, start=now(), end=now()
    )
    draft = old_mail(EMail, "special:all", balance=balance)
    draft.members.add(member_a)

    migrate()

    assert state(draft) == ("addr", "special:all", [member_a.pk], {})
    mail = CurrentEMail.objects.get(pk=draft.pk)
    assert not mail.has_deliveries
    # it is not sent until somebody has looked at it ...
    with pytest.raises(SendMailException, match="has to be reviewed"):
        mail.send()
    assert len(mailoutbox) == 0
    response = logged_in_client.get(
        reverse_url("office:mails.mail.view", kwargs={"pk": mail.pk})
    )
    assert "Please select the recipient again." in response.content.decode()

    # ... and selected the recipients again
    response = logged_in_client.post(
        reverse_url("office:mails.mail.view", kwargs={"pk": mail.pk}),
        {"to_type": "all", "subject": "Test", "text": "Text", "action": "send"},
    )

    assert response.status_code == 302, response.content.decode()
    mail.refresh_from_db()
    assert mail.sent is not None
    assert sorted(message.to[0] for message in mailoutbox) == [
        "a@example.org",
        "b@example.org",
    ]
    assert mail.delivered_to_members == {
        str(member_a.pk): "a@example.org",
        str(member_b.pk): "b@example.org",
    }


@pytest.mark.django_db
def test_review_of_a_migrated_draft_drops_its_stale_members(
    models, migrate, cleanup_balances, logged_in_client, configuration, mailoutbox
):
    """The old balance reminder for A became a mail to all members before it
    was sent. A is not an active member anymore when it is reviewed."""
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="a@example.org", name="A")
    member_b = Member.objects.create(email="b@example.org", name="B")
    activate(member_b)
    balance = MemberBalance.objects.create(
        member=member_a, amount=-10, start=now(), end=now()
    )
    draft = old_mail(EMail, "special:all", balance=balance)
    draft.members.add(member_a)
    migrate()
    assert state(draft) == ("addr", "special:all", [member_a.pk], {})

    response = logged_in_client.post(
        reverse_url("office:mails.mail.view", kwargs={"pk": draft.pk}),
        {"to_type": "all", "subject": "Test", "text": "Text", "action": "send"},
    )

    assert response.status_code == 302, response.content.decode()
    assert [message.to for message in mailoutbox] == [["b@example.org"]]
    # A was never sent this mail and does not have it in the history
    mail = CurrentEMail.objects.get(pk=draft.pk)
    assert mail.sent is not None
    assert [member.pk for member in mail.get_member_recipients()] == [member_b.pk]
    assert mail.delivered_to_members == {str(member_b.pk): "b@example.org"}
    assert not CurrentMember.objects.get(pk=member_a.pk).emails.exists()


@pytest.mark.django_db
def test_partly_delivered_mail_to_all_members_can_only_be_copied(
    models, migrate, logged_in_client, configuration, mailoutbox
):
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="family@example.org", name="A")
    member_b = Member.objects.create(email="family@example.org", name="B")
    activate(member_a)
    activate(member_b)
    unfinished = old_mail(EMail, "special:all", delivered_to=["family@example.org"])
    unfinished.members.add(member_a)
    migrate()
    mail = CurrentEMail.objects.get(pk=unfinished.pk)
    url = reverse_url("office:mails.mail.view", kwargs={"pk": mail.pk})

    # nobody is guessed to have received it, and it cannot be sent
    response = logged_in_client.get(
        reverse_url("office:mails.mail.send", kwargs={"pk": mail.pk}), follow=True
    )
    assert "has to be reviewed" in response.content.decode()
    assert len(mailoutbox) == 0

    # its recipients cannot be changed either, the delivery stays on record
    content = logged_in_client.get(url).content.decode()
    assert "byro cannot tell which members have" in content
    assert 'name="to_type"' not in content
    response = logged_in_client.post(
        url, {"to_type": "all", "subject": "Test", "text": "Text", "action": "send"}
    )
    mail.refresh_from_db()
    assert mail.to == "special:all"
    assert mail.sent is None
    assert mail.delivered_to == ["family@example.org"]
    assert list(mail.members.all()) == [mail.members.model.objects.get(pk=member_a.pk)]
    assert len(mailoutbox) == 0

    # the way out is a copy, which is a new mail without deliveries
    response = logged_in_client.get(
        reverse_url("office:mails.mail.copy", kwargs={"pk": mail.pk})
    )
    copy = CurrentEMail.objects.exclude(pk=mail.pk).get()
    assert not copy.has_deliveries
    assert not copy.members.exists()
    response = logged_in_client.post(
        reverse_url("office:mails.mail.view", kwargs={"pk": copy.pk}),
        {"to_type": "all", "subject": "Test", "text": "Text", "action": "send"},
    )
    assert response.status_code == 302, response.content.decode()
    copy.refresh_from_db()
    assert copy.sent is not None
    assert copy.delivered_to_members == {
        str(member_a.pk): "family@example.org",
        str(member_b.pk): "family@example.org",
    }
    assert len(mailoutbox) == 2


@pytest.mark.django_db
def test_addresses_are_never_matched_to_members(models, migrate):
    EMail, Member, MemberBalance = models
    member = Member.objects.create(email="member@example.org", name="A")
    draft = old_mail(EMail, "member@example.org")
    several = old_mail(EMail, "member@example.org, other@example.org")
    # sent before: the member was found by the address back then
    sent = old_mail(
        EMail, "member@example.org", sent=now(), delivered_to=["member@example.org"]
    )
    sent.members.add(member)

    migrate()

    assert state(draft) == ("addr", "member@example.org", [], {})
    assert state(several) == ("addr", "member@example.org, other@example.org", [], {})
    assert state(sent) == ("addr", "member@example.org", [member.pk], {})
    assert sent.delivered_to == ["member@example.org"]


@pytest.mark.django_db
def test_balance_reminder_draft_becomes_a_member_mail(
    models, migrate, cleanup_balances
):
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="family@example.org", name="A")
    member_b = Member.objects.create(email="family@example.org", name="B")
    mails = {}
    for member in (member_a, member_b):
        balance = MemberBalance.objects.create(
            member=member, amount=-10, start=now(), end=now()
        )
        mails[member.pk] = old_mail(EMail, member.email, balance=balance)
        mails[member.pk].members.add(member)

    migrate()

    assert state(mails[member_a.pk]) == ("member", "", [member_a.pk], {})
    assert state(mails[member_b.pk]) == ("member", "", [member_b.pk], {})


@pytest.mark.django_db
def test_changed_or_sent_balance_reminders_are_left_alone(
    models, migrate, cleanup_balances
):
    EMail, Member, MemberBalance = models
    member = Member.objects.create(email="member@example.org", name="A")
    other = Member.objects.create(email="member@example.org", name="B")

    def reminder(to, members, **kwargs):
        balance = MemberBalance.objects.create(
            member=member, amount=-10, start=now(), end=now()
        )
        mail = old_mail(EMail, to, balance=balance, **kwargs)
        mail.members.add(*members)
        return mail

    readdressed = reminder("other@example.org", [member])
    without_member = reminder("member@example.org", [])
    other_member = reminder("member@example.org", [other])
    sent = reminder(
        "member@example.org",
        [member],
        sent=now(),
        delivered_to=["member@example.org"],
    )

    migrate()

    assert state(readdressed) == ("addr", "other@example.org", [member.pk], {})
    assert state(without_member) == ("addr", "member@example.org", [], {})
    assert state(other_member) == ("addr", "member@example.org", [other.pk], {})
    assert state(sent) == ("addr", "member@example.org", [member.pk], {})


@pytest.mark.django_db
def test_migration_works_without_mails(models, migrate, reverse):
    EMail, Member, MemberBalance = models

    migrate()
    reverse()
    migrate()

    assert EMail.objects.count() == 0


# -- migrating backwards -------------------------------------------------------


def sent_member_mail(EMail, deliveries):
    """A sent mail of the new kind; ``deliveries`` maps members to addresses."""
    mail = EMail.objects.create(
        to_type="member",
        subject="Test",
        text="Text",
        sent=now(),
        delivered_to=[address.lower() for address in deliveries.values()],
        delivered_to_members={
            str(member.pk): address for member, address in deliveries.items()
        },
    )
    mail.members.add(*deliveries)
    return mail


@pytest.mark.django_db
def test_reverse_migration_restores_the_old_recipients(models, migrate, reverse):
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="family@example.org", name="A")
    member_b = Member.objects.create(email="family@example.org", name="B")
    special_all = old_mail(EMail, "special:all")
    special_member = old_mail(EMail, f"special:member:{member_a.pk}")
    address = old_mail(EMail, "one@example.org")
    review = old_mail(EMail, "special:all", delivered_to=["family@example.org"])
    migrate()
    sent_to_member = sent_member_mail(EMail, {member_b: "Old@example.org"})
    sent_to_family = sent_member_mail(
        EMail, {member_a: "family@example.org", member_b: "family@example.org"}
    )
    sent_to_all = EMail.objects.create(
        to_type="all",
        subject="Test",
        text="Text",
        sent=now(),
        delivered_to=["family@example.org", "family@example.org"],
        delivered_to_members={
            str(member_a.pk): "family@example.org",
            str(member_b.pk): "family@example.org",
        },
    )
    sent_to_all.members.add(member_a, member_b)

    reverse()

    assert dict(EMail.objects.values_list("pk", "to")) == {
        special_all.pk: "special:all",
        special_member.pk: f"special:member:{member_a.pk}",
        address.pk: "one@example.org",
        review.pk: "special:all",
        # sent mails look like the old code stored them: the address the mail
        # went to, even if the member has another one today
        sent_to_member.pk: "Old@example.org",
        sent_to_family.pk: "family@example.org, family@example.org",
        sent_to_all.pk: "special:all",
    }
    # the members stay as the history of the sent mails
    assert sorted(sent_to_family.members.values_list("pk", flat=True)) == sorted(
        [member_a.pk, member_b.pk]
    )


@pytest.mark.django_db
def test_migrating_backward_and_forward_again_keeps_the_recipients(
    models, migrate, reverse
):
    EMail, Member, MemberBalance = models
    member_a = Member.objects.create(email="family@example.org", name="A")
    member_b = Member.objects.create(email="family@example.org", name="B")
    draft_all = old_mail(EMail, "special:all")
    sent_all = old_mail(
        EMail, "special:all", sent=now(), delivered_to=["family@example.org"]
    )
    sent_all.members.add(member_a)
    review = old_mail(EMail, "special:all", delivered_to=["family@example.org"])
    review.members.add(member_a)
    draft_member = old_mail(EMail, f"special:member:{member_b.pk}")
    address = old_mail(EMail, "family@example.org")
    migrate()
    mails = (draft_all, sent_all, review, draft_member, address)
    migrated = [state(mail) for mail in mails]
    assert migrated == [
        ("all", "", [], {}),
        ("all", "", [member_a.pk], {}),
        ("addr", "special:all", [member_a.pk], {}),
        ("member", "", [member_b.pk], {}),
        ("addr", "family@example.org", [], {}),
    ]

    reverse()
    # migrating the schema backward and forward drops and adds both fields
    EMail.objects.update(to_type="addr", delivered_to_members={})
    migrate()

    assert [state(mail) for mail in mails] == migrated


def partly_delivered_shared_address(EMail, Member):
    member_a = Member.objects.create(email="family@example.org", name="A")
    member_b = Member.objects.create(email="family@example.org", name="B")
    mail = EMail.objects.create(
        to_type="member",
        subject="Test",
        text="Text",
        delivered_to=["family@example.org"],
        delivered_to_members={str(member_a.pk): "family@example.org"},
    )
    mail.members.add(member_a, member_b)
    return mail


def partly_delivered_to_all(EMail, Member):
    member_a = Member.objects.create(email="a@example.org", name="A")
    Member.objects.create(email="b@example.org", name="B")
    mail = EMail.objects.create(
        to_type="all",
        subject="Test",
        text="Text",
        delivered_to=["a@example.org"],
        delivered_to_members={str(member_a.pk): "a@example.org"},
    )
    mail.members.add(member_a)
    return mail


def partly_delivered_changed_address(EMail, Member):
    # delivered to A at the old address, B is still missing
    member_a = Member.objects.create(email="a-new@example.org", name="A")
    member_b = Member.objects.create(email="b@example.org", name="B")
    mail = EMail.objects.create(
        to_type="member",
        subject="Test",
        text="Text",
        delivered_to=["a-old@example.org"],
        delivered_to_members={str(member_a.pk): "a-old@example.org"},
    )
    mail.members.add(member_a, member_b)
    return mail


def several_members(EMail, Member):
    mail = EMail.objects.create(to_type="member", subject="Test", text="Text")
    mail.members.add(
        Member.objects.create(email="a@example.org", name="A"),
        Member.objects.create(email="b@example.org", name="B"),
    )
    return mail


def without_member(EMail, Member):
    return EMail.objects.create(to_type="member", subject="Test", text="Text")


def sent_without_recorded_address(EMail, Member):
    mail = EMail.objects.create(
        to_type="member", subject="Test", text="Text", sent=now()
    )
    mail.members.add(Member.objects.create(email="a@example.org", name="A"))
    return mail


def unknown_recipient_type(EMail, Member):
    return EMail.objects.create(to_type="other", subject="Test", text="Text")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "create_mail,reason",
    (
        (partly_delivered_shared_address, "delivered to some of its members"),
        (partly_delivered_to_all, "delivered to some of its members"),
        (partly_delivered_changed_address, "delivered to some of its members"),
        (several_members, "addressed to 2 members"),
        (without_member, "addressed to 0 members"),
        (sent_without_recorded_address, "is not recorded"),
        (unknown_recipient_type, "is unknown"),
    ),
)
def test_reverse_migration_refuses_what_the_old_schema_cannot_represent(
    models, reverse, create_mail, reason
):
    EMail, Member, MemberBalance = models
    # these could be converted, and come before and after the mail that cannot
    first = EMail.objects.create(to_type="all", subject="Test", text="Text")
    mail = create_mail(EMail, Member)
    recipient = Member.objects.create(email="member@example.org", name="Recipient")
    last = EMail.objects.create(to_type="member", subject="Test", text="Text")
    last.members.add(recipient)
    before = list(EMail.objects.order_by("pk").values())
    members_before = sorted(mail.members.values_list("pk", flat=True))

    with pytest.raises(migration_module.NotReversibleError) as error:
        reverse()

    assert f"mail {mail.pk}: " in str(error.value)
    assert reason in str(error.value)
    assert "nothing has been changed" in str(error.value)
    # no mail was touched, not even the ones that could have been converted
    assert list(EMail.objects.order_by("pk").values()) == before
    assert sorted(mail.members.values_list("pk", flat=True)) == members_before
    assert EMail.objects.get(pk=first.pk).to == ""
    assert EMail.objects.get(pk=last.pk).to == ""


# -- with the real schema --------------------------------------------------------


@pytest.fixture
def migrate_schema():
    """Run the real migrations, schema changes included, and return the
    historical models of the target. The latest state is restored afterwards."""

    def run(target):
        MigrationExecutor(connection).migrate([target])
        return MigrationLoader(connection).project_state(target).apps

    yield run
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def field_names(model):
    return {field.name for field in model._meta.get_fields()}


def send_failing_for(failing_member, mail):
    def fail(*args, member=None, **kwargs):
        if member == failing_member:
            raise SendMailException(f"{failing_member.name} cannot be reached.")
        return mail_send_task(*args, member=member, **kwargs)

    with patch("byro.mails.send.mail_send_task", side_effect=fail):
        with pytest.raises(SendMailException):
            mail.send()
    mail.refresh_from_db()


@pytest.mark.django_db(transaction=True)
def test_real_migration_backward_and_forward(migrate_schema, configuration, mailoutbox):
    member_a = CurrentMember.objects.create(email="a@example.org", name="A")
    member_b = CurrentMember.objects.create(email="b-old@example.org", name="B")
    activate(member_a)
    activate(member_b)
    draft_all = CurrentEMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    draft_member = CurrentEMail.for_member(member_a, subject="Test", text="Text")
    draft_member.save()
    address = CurrentEMail.objects.create(
        to="one@example.org", subject="Test", text="Text"
    )
    sent_member = CurrentEMail.for_member(member_b, subject="Test", text="Text")
    sent_member.save()
    sent_member.send()
    sent_all = CurrentEMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    sent_all.send()
    assert len(mailoutbox) == 3
    # the member changes the address after the mail was sent
    member_b.email = "b-new@example.org"
    member_b.save()

    old_apps = migrate_schema(BEFORE)

    OldEMail = old_apps.get_model("mails", "EMail")
    assert not {"to_type", "delivered_to_members"} & field_names(OldEMail)
    assert dict(OldEMail.objects.values_list("pk", "to")) == {
        draft_all.pk: "special:all",
        draft_member.pk: f"special:member:{member_a.pk}",
        address.pk: "one@example.org",
        sent_member.pk: "b-old@example.org",
        sent_all.pk: "special:all",
    }
    # (the historical member model of this state has no usable default order)
    assert list(
        OldEMail.objects.get(pk=sent_all.pk)
        .members.order_by("pk")
        .values_list("pk", flat=True)
    ) == [member_a.pk, member_b.pk]

    migrate_schema(MIGRATION)

    def current(mail):
        mail = CurrentEMail.objects.get(pk=mail.pk)
        return (
            mail.to_type,
            mail.to,
            [member.pk for member in mail.get_member_recipients()],
            mail.delivered_to_members,
        )

    assert current(draft_all) == ("all", "", [], {})
    assert current(draft_member) == ("member", "", [member_a.pk], {})
    assert current(address) == ("addr", "one@example.org", [], {})
    # sent mails come back the way the old code stored them: the address they
    # went to and the member as their history
    assert current(sent_member) == ("addr", "b-old@example.org", [member_b.pk], {})
    assert current(sent_all) == ("all", "", [member_a.pk, member_b.pk], {})
    # the drafts can still be sent to their members
    CurrentEMail.objects.get(pk=draft_member.pk).send()
    assert mailoutbox[-1].to == ["a@example.org"]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("shared_address", (True, False))
def test_real_migration_backward_refuses_a_partly_delivered_member_mail(
    migrate_schema, configuration, mailoutbox, shared_address
):
    """A was reached, B was not. The old schema would record this as one
    delivered address and skip B as well when the mail is sent again."""
    member_a = CurrentMember.objects.create(email="family@example.org", name="A")
    member_b = CurrentMember.objects.create(
        email="family@example.org" if shared_address else "b@example.org", name="B"
    )
    mail = CurrentEMail.for_member(member_a, subject="Test", text="Text")
    mail.save()
    mail.members.add(member_b)
    send_failing_for(member_b, mail)
    assert mail.delivered_to_members == {str(member_a.pk): "family@example.org"}
    # a mail that could be converted on its own
    draft_all = CurrentEMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    before = list(CurrentEMail.objects.order_by("pk").values())

    with pytest.raises(migration_module.NotReversibleError) as error:
        migrate_schema(BEFORE)

    assert f"mail {mail.pk}: it has been delivered to some of its members" in str(
        error.value
    )
    # the migration is still applied, the schema and all mails are untouched
    assert MIGRATION in MigrationRecorder(connection).applied_migrations()
    assert list(CurrentEMail.objects.order_by("pk").values()) == before
    assert CurrentEMail.objects.get(pk=draft_all.pk).to == ""
    mail = CurrentEMail.objects.get(pk=mail.pk)
    assert mail.get_member_recipients() == [member_a, member_b]

    # and the mail still reaches the member that is missing, and only that one
    mail.send()

    mail.refresh_from_db()
    assert mail.sent is not None
    assert [message.to for message in mailoutbox] == [
        ["family@example.org"],
        [member_b.email],
    ]
    assert member_b.profile_memberpage.get_url() in mailoutbox[1].body


@pytest.mark.django_db(transaction=True)
def test_real_migration_backward_refuses_a_partly_delivered_mail_to_all_members(
    migrate_schema, configuration, mailoutbox
):
    member_a = CurrentMember.objects.create(email="a@example.org", name="A")
    member_b = CurrentMember.objects.create(email="b@example.org", name="B")
    activate(member_a)
    activate(member_b)
    mail = CurrentEMail.objects.create(
        to_type=RecipientType.ALL_MEMBERS, subject="Test", text="Text"
    )
    send_failing_for(member_b, mail)
    before = list(CurrentEMail.objects.order_by("pk").values())

    with pytest.raises(migration_module.NotReversibleError):
        migrate_schema(BEFORE)

    assert MIGRATION in MigrationRecorder(connection).applied_migrations()
    assert list(CurrentEMail.objects.order_by("pk").values()) == before
    assert list(mail.members.all()) == [member_a]
