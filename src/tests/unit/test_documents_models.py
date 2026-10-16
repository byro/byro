import datetime

import pytest
from django.core import mail
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from freezegun import freeze_time

from byro.documents.models import Document
from byro.mails.models import EMail, RecipientType
from byro.mails.send import SendMailException


@pytest.fixture
def document():
    f = SimpleUploadedFile("testresource.txt", b"a resource")
    d = Document.objects.create(document=f, title="Test document")
    yield d
    d.delete()


@pytest.mark.django_db
@pytest.mark.parametrize("immediately", (True, False))
def test_document_send(document, member, immediately):
    count = EMail.objects.count()
    document.member = member
    document.save()
    assert "Document" in document.get_display()
    document.send(immediately=immediately)
    assert EMail.objects.count() == count + 1
    mail = EMail.objects.last()
    assert mail.to_type == RecipientType.MEMBER
    assert mail.to == ""
    assert mail.get_member_recipients() == [member]
    assert mail.attachments.count() == 1
    assert (mail.sent is None) is not immediately


@pytest.mark.django_db
def test_document_date_defaults_to_a_date(document):
    # a plain date from the start, not a datetime that only turns into a date
    # once the document is loaded from the database
    assert type(document.date) is datetime.date
    date = document.date

    document.refresh_from_db()
    assert type(document.date) is datetime.date
    assert document.date == date


@pytest.mark.parametrize(
    "time_zone,expected",
    (
        ("Europe/Berlin", datetime.date(2024, 1, 1)),
        ("America/New_York", datetime.date(2023, 12, 31)),
        ("UTC", datetime.date(2023, 12, 31)),
    ),
)
@pytest.mark.django_db
def test_document_date_defaults_to_the_local_date(settings, time_zone, expected):
    settings.TIME_ZONE = time_zone
    # half past midnight in Berlin, still the day before in UTC and New York
    with freeze_time("2023-12-31 23:30:00"):
        document = Document.objects.create(
            document=SimpleUploadedFile("testresource.txt", b"a resource"),
            title="Test document",
        )

    assert document.date == expected
    document.refresh_from_db()
    assert document.date == expected


@pytest.mark.django_db
def test_document_without_date_can_be_stored_and_loaded():
    document = Document.objects.create(
        document=SimpleUploadedFile("testresource.txt", b"a resource"),
        title="Test document",
        date=None,
    )

    assert Document.objects.get(pk=document.pk).date is None
    # the model orders by date
    assert list(Document.objects.all()) == [document]


PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


@pytest.mark.parametrize("storage", (None, InMemoryStorage))
@pytest.mark.parametrize(
    "name,title,content,expected_name,expected_type",
    (
        pytest.param(
            "scan0042.pdf",
            "Aufnahmeantrag Max Müller",
            PDF,
            "Aufnahmeantrag Max Müller.pdf",
            "application/pdf",
            id="type-from-the-extension",
        ),
        pytest.param(
            "scan0042", "Letter", PDF, "Letter", "application/pdf", id="type-detected"
        ),
        pytest.param(
            "notes.txt", "Notes", b"some notes", "Notes.txt", "text/plain", id="text"
        ),
    ),
)
@pytest.mark.django_db
def test_document_attachment_is_named_like_a_download(
    configuration,
    member,
    use_document_storage,
    storage,
    name,
    title,
    content,
    expected_name,
    expected_type,
):
    if storage:
        use_document_storage(storage())
    document = Document.objects.create(
        document=SimpleUploadedFile(name, content), title=title, member=member
    )

    document.send(immediately=True)

    (filename, body, mimetype), *_ = mail.outbox[-1].attachments
    assert filename == expected_name
    assert mimetype == expected_type
    assert (body.encode() if isinstance(body, str) else body) == content
    assert document.document.name.rsplit("/", 1)[-1] not in filename


# -- the mail text comes from the document delivery template -----------------


@pytest.fixture
def delivery_template(configuration):
    return configuration.document_delivery_template


@pytest.fixture
def member_document(configuration, member):
    d = Document.objects.create(
        document=SimpleUploadedFile("testresource.txt", b"a resource"),
        title="Test document",
        member=member,
    )
    yield d
    d.delete()


@pytest.mark.django_db
def test_document_send_uses_the_default_delivery_template(
    configuration, member, member_document, delivery_template
):
    mail = member_document.send()

    assert mail.template == delivery_template
    assert mail.subject == "[Association Name] Your document"
    assert mail.text == (
        f"Hi, {member.name},\n\n"
        "Please find attached a document we wanted to send you/that you requested."
        "\n\nThank you,\nAssociation Name"
    )
    assert mail.to_type == RecipientType.MEMBER
    assert mail.get_member_recipients() == [member]
    assert list(mail.attachments.all()) == [member_document]


@pytest.mark.django_db
def test_document_send_renders_the_default_template_in_the_configured_language(
    configuration, member_document
):
    configuration.language = "de"
    configuration.save()

    mail = member_document.send()

    assert mail.subject == "[Association Name] Dein Dokument"
    assert "Im Anhang befindet sich ein Dokument für dich." in mail.text


@pytest.mark.django_db
def test_document_send_uses_an_edited_delivery_template(
    member, member_document, delivery_template
):
    delivery_template.subject = "Document for {name}"
    delivery_template.text = "{association} sends you a document."
    delivery_template.reply_to = "office@example.org"
    delivery_template.bcc = "archive@example.org"
    delivery_template.save()

    mail = member_document.send()

    assert mail.subject == f"Document for {member.name}"
    assert mail.text == "Association Name sends you a document."
    assert mail.reply_to == "office@example.org"
    assert mail.bcc == "archive@example.org"


@pytest.mark.django_db
def test_document_send_to_an_address_names_the_member_or_the_address(
    member, member_document, document, delivery_template
):
    delivery_template.text = "Hello {name}"
    delivery_template.save()

    mail = member_document.send(email="someone@example.org")

    assert mail.text == f"Hello {member.name}"
    assert mail.to_type == RecipientType.ADDRESS
    assert mail.to == "someone@example.org"
    assert not mail.members.exists()
    assert list(mail.attachments.all()) == [member_document]

    mail = document.send(email="someone@example.org")

    assert mail.text == "Hello someone@example.org"
    assert mail.to == "someone@example.org"


@pytest.mark.django_db
def test_document_send_uses_an_explicit_subject(member_document):
    mail = member_document.send(subject="Your {requested} document")

    mail.refresh_from_db()
    assert mail.subject == "Your {requested} document"


@pytest.mark.django_db
def test_document_send_uses_an_explicit_text(member_document):
    mail = member_document.send(text="Here it is: {not a variable}")

    mail.refresh_from_db()
    assert mail.text == "Here it is: {not a variable}"
    assert mail.subject == "[Association Name] Your document"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "broken,overrides",
    (
        pytest.param(("subject",), {"subject": "Subject"}, id="subject"),
        pytest.param(("text",), {"text": "Text"}, id="text"),
        pytest.param(
            ("subject", "text"), {"subject": "Subject", "text": "Text"}, id="both"
        ),
    ),
)
def test_document_send_does_not_render_a_replaced_template_field(
    member_document, delivery_template, broken, overrides
):
    for field in broken:
        setattr(delivery_template, field, "{incorrect_key} {")
    delivery_template.save()

    mail = member_document.send(**overrides)

    mail.refresh_from_db()
    for field, value in overrides.items():
        assert getattr(mail, field) == value
    assert list(mail.attachments.all()) == [member_document]


@pytest.mark.django_db
def test_document_send_fails_for_a_broken_template_field_that_is_not_replaced(
    member_document, delivery_template
):
    delivery_template.subject = "{incorrect_key}"
    delivery_template.save()
    count = EMail.objects.count()

    with pytest.raises(SendMailException):
        member_document.send(text="Text")

    assert EMail.objects.count() == count


@pytest.mark.django_db
def test_document_send_without_delivery_template_uses_the_default(
    configuration, member, member_document
):
    configuration.document_delivery_template = None
    configuration.save()

    mail = member_document.send()

    assert mail.template is None
    assert mail.subject == "[Association Name] Your document"
    assert mail.text.startswith(f"Hi, {member.name},\n\n")


# Behaviour preservation: plugins may still read the old attribute.
def test_document_template_keeps_its_value():
    assert isinstance(Document.template, str)
    assert Document.template.format(name="Jona", association="Verein") == (
        "Hi, Jona,\n\n"
        "Please find attached a document we wanted to send you/that you requested."
        "\n\nThank you,\nVerein"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("email", (None, ""))
def test_document_without_member_and_address_is_not_sent(
    configuration, document, email
):
    count = EMail.objects.count()

    with pytest.raises(ValueError, match="explicit address"):
        document.send(email=email)

    assert EMail.objects.count() == count
