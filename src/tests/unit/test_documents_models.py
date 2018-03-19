import pytest

from byro.documents.models import Document
from byro.mails.models import EMail


@pytest.fixture
def document():
    d = Document.objects.create(
        document=__file__,
        title='Test document',
    )
    yield d
    d.delete()


@pytest.mark.django_db
def test_document_send(document, member):
    count = EMail.objects.count()
    document.member = member
    document.save()
    assert 'Document' in str(document)
    document.send()
    assert EMail.objects.count() == count + 1
    mail = EMail.objects.last()
    assert mail.to == document.member.email
    assert mail.attachments.count() == 1
