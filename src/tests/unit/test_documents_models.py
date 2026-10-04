import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from freezegun import freeze_time

from byro.documents.models import Document
from byro.mails.models import EMail


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
    assert mail.to == document.member.email
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
