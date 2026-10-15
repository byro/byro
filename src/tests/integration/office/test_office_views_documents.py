import base64
import io
import zipfile

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


PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg=="
)
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
GIF = b"GIF89a\x01\x00\x01\x00\x00\x00\x00;"
WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\x30\x01\x00\x9d\x01\x2a"
HTML = b"<!DOCTYPE html><html><body><p>Minutes</p></body></html>"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>'


def zip_archive():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("minutes.txt", "some minutes")
    return buffer.getvalue()


def create_document(name, content):
    return Document.objects.create(
        document=SimpleUploadedFile(name, content), title="A document"
    )


def download(client, document):
    return client.get(
        reverse(
            "office:documents.download",
            kwargs={"pk": document.pk, "filename": document.basename},
        )
    )


@pytest.mark.parametrize(
    "name,content,content_type",
    (
        pytest.param("letter.pdf", PDF, "application/pdf", id="pdf"),
        pytest.param("photo.png", PNG, "image/png", id="png"),
        pytest.param("photo.jpg", JPEG, "image/jpeg", id="jpeg"),
        pytest.param("photo.gif", GIF, "image/gif", id="gif"),
        pytest.param("photo.webp", WEBP, "image/webp", id="webp"),
        # the content decides, not the name of the file
        pytest.param("letter.html", PDF, "application/pdf", id="pdf-named-html"),
    ),
)
@pytest.mark.django_db
def test_document_download_shows_pdf_files_and_images(
    logged_in_client, name, content, content_type
):
    document = create_document(name, content)

    response = download(logged_in_client, document)

    assert response.status_code == 200
    assert response["Content-Type"] == content_type
    assert response["Content-Disposition"] == f'inline; filename="{document.basename}"'
    assert response["X-Content-Type-Options"] == "nosniff"
    # the preview on the detail page is a frame of byro itself
    assert response["X-Frame-Options"] == "SAMEORIGIN"
    assert int(response["Content-Length"]) == len(content)
    assert b"".join(response.streaming_content) == content


@pytest.mark.parametrize(
    "name,content",
    (
        pytest.param("minutes.html", HTML, id="html"),
        pytest.param("logo.svg", SVG, id="svg"),
        pytest.param("minutes.txt", b"some minutes", id="text"),
        pytest.param("minutes.zip", zip_archive(), id="zip"),
        # the content decides, not the name of the file
        pytest.param("minutes.pdf", HTML, id="html-named-pdf"),
        pytest.param("photo.png", SVG, id="svg-named-png"),
    ),
)
@pytest.mark.django_db
def test_document_download_offers_other_files_as_download(
    logged_in_client, name, content
):
    document = create_document(name, content)

    response = download(logged_in_client, document)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/octet-stream"
    assert (
        response["Content-Disposition"] == f'attachment; filename="{document.basename}"'
    )
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert int(response["Content-Length"]) == len(content)
    assert b"".join(response.streaming_content) == content


@pytest.mark.parametrize(
    "name,content,preview",
    (
        pytest.param("letter.pdf", PDF, True, id="pdf"),
        pytest.param("photo.png", PNG, True, id="png"),
        pytest.param("logo.svg", SVG, False, id="svg"),
        pytest.param("minutes.html", HTML, False, id="html"),
    ),
)
@pytest.mark.django_db
def test_document_detail_previews_only_what_the_browser_may_show(
    logged_in_client, name, content, preview
):
    document = create_document(name, content)

    response = logged_in_client.get(
        reverse("office:documents.detail", kwargs={"pk": document.pk})
    )

    assert response.status_code == 200
    content = response.content.decode()
    url = reverse(
        "office:documents.download",
        kwargs={"pk": document.pk, "filename": document.basename},
    )
    assert url in content
    assert ("<iframe" in content) is preview


@pytest.mark.django_db
def test_document_download_requires_login(client):
    document = create_document("letter.pdf", PDF)

    response = download(client, document)

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("common:login"))
