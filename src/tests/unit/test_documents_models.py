import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

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
