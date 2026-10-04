import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import include, path, reverse
from django.utils.timezone import now

from byro.documents.models import Document
from byro.office.views.documents import DocumentUploadView

pytestmark = pytest.mark.usefixtures("configuration")

# URLconf for tests marked with ``pytest.mark.urls(__name__)``: the regular
# byro URLs plus a second, unnamed path to the document upload.
urlpatterns = [
    path("alias/document-upload", DocumentUploadView.as_view()),
    path("", include("byro.urls")),
]


def document_upload_data():
    return {
        "document": SimpleUploadedFile("minutes.txt", b"some minutes"),
        "date": str(now().date()),
        "title": "Minutes",
        "category": "byro.documents.misc",
        "direction": "incoming",
    }


@pytest.mark.django_db
def test_document_upload_redirects_to_upload_page(logged_in_client):
    response = logged_in_client.post(
        reverse("office:documents.add"), document_upload_data()
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("office:documents.add")
    assert Document.objects.get().title == "Minutes"


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_document_upload_redirects_to_named_route_from_other_path(logged_in_client):
    response = logged_in_client.post("/alias/document-upload", document_upload_data())
    assert response.status_code == 302
    assert response["Location"] == reverse("office:documents.add")
    assert response["Location"] == "/documents/add"
    assert Document.objects.get().title == "Minutes"


@pytest.fixture
def undated_document(member):
    """The model allows documents without a date, for example from a plugin."""
    return Document.objects.create(
        document=SimpleUploadedFile("undated.txt", b"an undated document"),
        title="Undated letter",
        date=None,
        member=member,
    )


@pytest.mark.django_db
def test_document_detail_without_date(logged_in_client, undated_document):
    response = logged_in_client.get(
        reverse("office:documents.detail", kwargs={"pk": undated_document.pk})
    )

    assert response.status_code == 200
    assert "Undated letter" in response.content.decode()


@pytest.mark.django_db
def test_member_documents_list_without_date(logged_in_client, member, undated_document):
    dated = Document.objects.create(
        document=SimpleUploadedFile("dated.txt", b"a dated document"),
        title="Dated letter",
        date=now().date(),
        member=member,
    )

    response = logged_in_client.get(
        reverse("office:members.documents", kwargs={"pk": member.pk})
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Undated letter" in content
    assert dated.title in content
