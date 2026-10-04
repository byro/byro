import datetime
import json
import os
from glob import glob
from hashlib import sha512
from uuid import uuid4

import pytest
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from byro.common.models import LogEntry
from byro.documents.models import Document
from byro.members.models import Member

CONTENT = b"%PDF-1.4 membership application"
RESPONSE_FIELDS = {
    "id",
    "title",
    "date",
    "category",
    "direction",
    "content_hash",
    "filename",
}


def list_url(member_pk):
    return reverse("api:member-documents-list", kwargs={"member_pk": member_pk})


def detail_url(member_pk, pk):
    return reverse(
        "api:member-documents-detail", kwargs={"member_pk": member_pk, "pk": pk}
    )


def stored_files(stem):
    """The files in the document storage that an upload named ``stem`` left."""
    pattern = os.path.join(settings.MEDIA_ROOT, "documents", "**", f"{stem}*")
    return glob(pattern, recursive=True)


def api_client_for(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def api_user(create_user):
    return create_user("api_user", is_staff=True)


@pytest.fixture
def api_client(api_user):
    return api_client_for(api_user)


@pytest.fixture
def other_member():
    return Member.objects.create(
        email="other@hacker.space", number="2", name="Some One Else"
    )


@pytest.fixture
def stem():
    """A file name that only this test uploads, to find its file again."""
    return f"upload-{uuid4().hex}"


@pytest.fixture
def payload(stem):
    def build(**overrides):
        data = {
            "document": SimpleUploadedFile(f"{stem}.pdf", CONTENT),
            "title": "Membership application",
            "date": "2022-04-15",
            "category": "byro.documents.registration_form",
            "direction": "incoming",
        }
        data.update(overrides)
        return {key: value for key, value in data.items() if value is not None}

    return build


@pytest.fixture
def create_document():
    def create(member, title="Existing document", **kwargs):
        upload = SimpleUploadedFile(f"existing-{uuid4().hex}.txt", b"existing")
        return Document.objects.create(
            document=upload, title=title, member=member, **kwargs
        )

    return create


@pytest.mark.django_db
def test_upload_creates_document_for_member(api_client, member, payload, stem):
    response = api_client.post(list_url(member.pk), payload(), format="multipart")

    assert response.status_code == 201
    document = Document.objects.get()
    assert document.member == member
    data = response.json()
    assert set(data) == RESPONSE_FIELDS
    assert data == {
        "id": document.pk,
        "title": "Membership application",
        "date": "2022-04-15",
        "category": "byro.documents.registration_form",
        "direction": "incoming",
        "content_hash": document.content_hash,
        "filename": f"{stem}.pdf",
    }
    assert stored_files(stem) == [document.document.path]
    with open(document.document.path, "rb") as stored:
        assert stored.read() == CONTENT


@pytest.mark.parametrize("direction", ("incoming", "outgoing", "other"))
@pytest.mark.django_db
def test_upload_stores_metadata(api_client, member, payload, direction):
    response = api_client.post(
        list_url(member.pk),
        payload(
            title="Statement 2021",
            date="2021-12-31",
            category="byro.bookkeeping.account.statement",
            direction=direction,
        ),
        format="multipart",
    )

    assert response.status_code == 201
    document = Document.objects.get()
    assert document.title == "Statement 2021"
    assert document.date == datetime.date(2021, 12, 31)
    assert document.category == "byro.bookkeeping.account.statement"
    assert document.direction == direction


@pytest.mark.django_db
def test_upload_defaults(api_client, member, payload):
    response = api_client.post(
        list_url(member.pk),
        payload(date=None, category=None, direction=None),
        format="multipart",
    )

    assert response.status_code == 201
    today = timezone.localdate()
    data = response.json()
    assert data["date"] == today.isoformat()
    assert data["category"] == "byro.documents.misc"
    assert data["direction"] == "outgoing"
    document = Document.objects.get()
    document.refresh_from_db()
    assert document.date == today
    assert document.category == "byro.documents.misc"
    assert document.direction == "outgoing"


@pytest.mark.django_db
def test_upload_empty_date_uses_default(api_client, member, payload):
    response = api_client.post(
        list_url(member.pk), payload(date=""), format="multipart"
    )

    assert response.status_code == 201
    assert Document.objects.get().date == timezone.localdate()


@pytest.mark.django_db
def test_upload_computes_content_hash(api_client, member, payload):
    response = api_client.post(list_url(member.pk), payload(), format="multipart")

    assert response.status_code == 201
    expected = f"sha512:{sha512(CONTENT).hexdigest()}"
    assert response.json()["content_hash"] == expected
    document = Document.objects.get()
    assert document.content_hash == expected
    assert document.content_hash_ok


@pytest.mark.django_db
def test_upload_assigns_member_from_url(api_client, member, other_member, payload):
    response = api_client.post(list_url(member.pk), payload(), format="multipart")

    assert response.status_code == 201
    assert Document.objects.get().member == member
    assert not other_member.documents.exists()


@pytest.mark.parametrize(
    "field,value",
    (
        pytest.param("member", "other", id="other-member"),
        pytest.param("member", "same", id="member-of-the-url"),
        pytest.param("member", "", id="empty-member"),
        pytest.param("content_hash", "sha512:" + "0" * 128, id="content-hash"),
        pytest.param("content_hash", "", id="empty-content-hash"),
    ),
)
@pytest.mark.django_db
def test_upload_rejects_server_managed_fields(
    api_client, member, other_member, payload, stem, field, value
):
    value = {"other": other_member.pk, "same": member.pk}.get(value, value)
    log_entries = LogEntry.objects.count()

    response = api_client.post(
        list_url(member.pk), payload(**{field: value}), format="multipart"
    )

    assert response.status_code == 400
    assert list(response.json()) == [field]
    assert not Document.objects.exists()
    assert stored_files(stem) == []
    assert LogEntry.objects.count() == log_entries

    # the same request without the field is a valid upload
    response = api_client.post(list_url(member.pk), payload(), format="multipart")
    assert response.status_code == 201
    document = Document.objects.get()
    assert document.member == member
    assert document.content_hash == f"sha512:{sha512(CONTENT).hexdigest()}"
    assert stored_files(stem) == [document.document.path]


@pytest.mark.django_db
def test_upload_writes_audit_log(api_client, api_user, member, payload):
    response = api_client.post(list_url(member.pk), payload(), format="multipart")

    assert response.status_code == 201
    document = Document.objects.get()

    # the same entry as an upload in the member view of the office
    entry = LogEntry.objects.get(action_type="byro.members.document.created")
    assert entry.content_object == member
    assert entry.user == api_user
    assert entry.data["source"] == str(api_user)
    assert entry.data["content_hash"] == document.content_hash
    assert entry.data["document"]["ref"] == ["documents", "document", document.pk]

    # written by Document.save()
    entry = LogEntry.objects.get(action_type="byro.documents.document.stored")
    assert entry.content_object == document
    assert entry.data["content_hash"] == document.content_hash
    assert entry.data["member"]["ref"] == ["members", "member", member.pk]


@pytest.mark.django_db
def test_list_returns_documents_of_member(
    api_client, member, other_member, create_document
):
    older = create_document(member, title="Older", date=datetime.date(2020, 1, 1))
    newer = create_document(member, title="Newer", date=datetime.date(2021, 1, 1))
    create_document(other_member, title="Not mine", date=datetime.date(2022, 1, 1))
    create_document(None, title="Unrelated", date=datetime.date(2022, 1, 1))

    response = api_client.get(list_url(member.pk))

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"count", "next", "previous", "results"}
    assert data["count"] == 2
    assert [entry["id"] for entry in data["results"]] == [newer.pk, older.pk]
    assert all(set(entry) == RESPONSE_FIELDS for entry in data["results"])
    assert data["results"][0]["content_hash"] == newer.content_hash


@pytest.mark.django_db
def test_list_is_empty_for_member_without_documents(
    api_client, member, other_member, create_document
):
    create_document(other_member)

    response = api_client.get(list_url(member.pk))

    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_detail_returns_document(api_client, member, create_document):
    document = create_document(
        member,
        title="Letter",
        date=datetime.date(2020, 5, 17),
        category="byro.documents.misc",
        direction="incoming",
    )

    response = api_client.get(detail_url(member.pk, document.pk))

    assert response.status_code == 200
    assert response.json() == {
        "id": document.pk,
        "title": "Letter",
        "date": "2020-05-17",
        "category": "byro.documents.misc",
        "direction": "incoming",
        "content_hash": document.content_hash,
        "filename": document.basename,
    }


@pytest.mark.django_db
def test_detail_does_not_return_document_of_other_member(
    api_client, member, other_member, create_document
):
    document = create_document(other_member)

    response = api_client.get(detail_url(member.pk, document.pk))
    assert response.status_code == 404

    # the document exists, under its own member
    response = api_client.get(detail_url(other_member.pk, document.pk))
    assert response.status_code == 200
    assert response.json()["id"] == document.pk


@pytest.mark.django_db
def test_detail_does_not_return_document_without_member(
    api_client, member, create_document
):
    document = create_document(None)

    response = api_client.get(detail_url(member.pk, document.pk))

    assert response.status_code == 404


@pytest.mark.django_db
def test_requires_a_token(member, create_document, payload, stem):
    document = create_document(member)
    client = APIClient()

    assert client.get(list_url(member.pk)).status_code == 401
    assert client.get(detail_url(member.pk, document.pk)).status_code == 401
    response = client.post(list_url(member.pk), payload(), format="multipart")
    assert response.status_code == 401
    assert Document.objects.count() == 1
    assert stored_files(stem) == []


@pytest.mark.django_db
def test_requires_a_token_before_looking_up_the_member(payload):
    # no hint whether the member exists
    client = APIClient()

    assert client.get(list_url(424242)).status_code == 401
    response = client.post(list_url(424242), payload(), format="multipart")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "is_staff,is_superuser,allowed",
    (
        pytest.param(False, False, False, id="no-flags"),
        pytest.param(True, False, True, id="staff"),
        pytest.param(False, True, True, id="superuser-without-staff"),
    ),
)
@pytest.mark.django_db
def test_requires_backend_access(
    create_user, member, create_document, payload, stem, is_staff, is_superuser, allowed
):
    document = create_document(member)
    user = create_user("some_user", is_staff=is_staff, is_superuser=is_superuser)
    client = api_client_for(user)

    response = client.get(list_url(member.pk))
    assert response.status_code == (200 if allowed else 403)
    response = client.get(detail_url(member.pk, document.pk))
    assert response.status_code == (200 if allowed else 403)
    response = client.post(list_url(member.pk), payload(), format="multipart")
    assert response.status_code == (201 if allowed else 403)
    assert Document.objects.count() == (2 if allowed else 1)
    assert len(stored_files(stem)) == (1 if allowed else 0)


@pytest.mark.django_db
def test_ignores_browser_session(
    superuser_client, configuration, member, payload, stem
):
    assert superuser_client.get(list_url(member.pk)).status_code == 401
    response = superuser_client.post(list_url(member.pk), payload())
    assert response.status_code == 401
    assert not Document.objects.exists()
    assert stored_files(stem) == []


@pytest.mark.django_db
def test_unknown_member(api_client, member, create_document, payload, stem):
    document = create_document(member)
    unknown = member.pk + 1000
    log_entries = LogEntry.objects.count()

    assert api_client.get(list_url(unknown)).status_code == 404
    assert api_client.get(detail_url(unknown, document.pk)).status_code == 404
    response = api_client.post(list_url(unknown), payload(), format="multipart")
    assert response.status_code == 404
    assert Document.objects.count() == 1
    assert stored_files(stem) == []
    assert LogEntry.objects.count() == log_entries

    # the same upload works for the existing member
    response = api_client.post(list_url(member.pk), payload(), format="multipart")
    assert response.status_code == 201


@pytest.mark.django_db
def test_unknown_document(api_client, member, create_document):
    document = create_document(member)

    response = api_client.get(detail_url(member.pk, document.pk + 1000))

    assert response.status_code == 404


@pytest.mark.parametrize(
    "overrides,field",
    (
        pytest.param({"document": None}, "document", id="no-file"),
        pytest.param({"document": "not a file"}, "document", id="file-is-text"),
        pytest.param({"title": None}, "title", id="no-title"),
        pytest.param({"title": ""}, "title", id="blank-title"),
        pytest.param({"title": "x" * 301}, "title", id="title-too-long"),
        pytest.param({"date": "15.04.2022"}, "date", id="invalid-date"),
        pytest.param({"category": "byro.unknown"}, "category", id="unknown-category"),
        pytest.param({"direction": "sideways"}, "direction", id="invalid-direction"),
    ),
)
@pytest.mark.django_db
def test_upload_validation(api_client, member, payload, stem, overrides, field):
    log_entries = LogEntry.objects.count()

    response = api_client.post(
        list_url(member.pk), payload(**overrides), format="multipart"
    )

    assert response.status_code == 400
    assert list(response.json()) == [field]
    assert not Document.objects.exists()
    assert stored_files(stem) == []
    assert LogEntry.objects.count() == log_entries


@pytest.mark.django_db
def test_upload_rejects_empty_file(api_client, member, payload, stem):
    response = api_client.post(
        list_url(member.pk),
        payload(document=SimpleUploadedFile(f"{stem}.pdf", b"")),
        format="multipart",
    )

    assert response.status_code == 400
    assert list(response.json()) == ["document"]
    assert not Document.objects.exists()
    assert stored_files(stem) == []


@pytest.mark.django_db
def test_upload_requires_multipart(api_client, member):
    response = api_client.post(
        list_url(member.pk), {"title": "No file in JSON"}, format="json"
    )

    assert response.status_code == 415
    assert not Document.objects.exists()


@pytest.mark.django_db
def test_documents_cannot_be_changed_or_deleted(
    api_client, member, create_document, payload
):
    document = create_document(member, title="Unchanged")
    path = document.document.path
    url = detail_url(member.pk, document.pk)

    assert api_client.put(url, payload(), format="multipart").status_code == 405
    response = api_client.patch(url, {"title": "Changed"}, format="multipart")
    assert response.status_code == 405
    assert api_client.delete(url).status_code == 405
    assert api_client.delete(list_url(member.pk)).status_code == 405

    document.refresh_from_db()
    assert document.title == "Unchanged"
    assert os.path.exists(path)


def fail_in_member_log(monkeypatch):
    """Fails after Document.save() stored the row and its ".stored" entry."""

    def log(self, context, action, **kwargs):
        raise RuntimeError("audit log failed")

    monkeypatch.setattr(Member, "log", log)


def fail_in_document_save(monkeypatch):
    """Fails inside Document.save(), after the row was inserted."""

    def log(self, context, action, **kwargs):
        raise RuntimeError("audit log failed")

    monkeypatch.setattr(Document, "log", log)


@pytest.mark.parametrize("fail", (fail_in_member_log, fail_in_document_save))
@pytest.mark.django_db
def test_failed_upload_rolls_back_document_and_log_entries(
    api_user, member, payload, monkeypatch, fail
):
    log_entries = LogEntry.objects.count()

    with monkeypatch.context() as patch:
        fail(patch)
        with pytest.raises(RuntimeError, match="audit log failed"):
            api_client_for(api_user).post(
                list_url(member.pk), payload(), format="multipart"
            )

    # the document, its ".stored" entry and the member entry exist together
    # or not at all
    assert not Document.objects.exists()
    assert not LogEntry.objects.filter(
        action_type="byro.documents.document.stored"
    ).exists()
    assert not LogEntry.objects.filter(
        action_type="byro.members.document.created"
    ).exists()
    assert LogEntry.objects.count() == log_entries

    # without the failure the same upload creates all three
    response = api_client_for(api_user).post(
        list_url(member.pk), payload(), format="multipart"
    )
    assert response.status_code == 201
    document = Document.objects.get()
    assert os.path.exists(document.document.path)
    assert LogEntry.objects.count() == log_entries + 2


def files_in(storage, directory=""):
    directories, files = storage.listdir(directory)
    found = {os.path.join(directory, name) for name in files}
    for name in directories:
        found |= files_in(storage, os.path.join(directory, name))
    return found


@pytest.mark.parametrize(
    "allow_overwrite",
    (
        pytest.param(False, id="default-storage"),
        pytest.param(True, id="overwriting-storage"),
    ),
)
@pytest.mark.django_db
def test_failed_upload_deletes_nothing_from_storage(
    api_user, member, payload, stem, monkeypatch, tmp_path, allow_overwrite
):
    """The API has no code path that deletes from the storage.

    That is all this test covers, also with the overwriting storage: a failed
    upload must not remove the file of an existing document. An overwriting
    storage still lets an upload replace the content of an existing file with
    the same name, in the API as in the office. This is NOT fixed here, it
    belongs to the follow-up issue on the document storage.
    """
    storage = FileSystemStorage(location=tmp_path, allow_overwrite=allow_overwrite)
    monkeypatch.setattr(Document._meta.get_field("document"), "storage", storage)
    existing = Document.objects.create(
        document=SimpleUploadedFile(f"{stem}.pdf", b"existing content"),
        title="Existing",
        member=member,
    )
    before = files_in(storage)
    assert before == {existing.document.name}

    with monkeypatch.context() as patch:
        fail_in_member_log(patch)
        with pytest.raises(RuntimeError, match="audit log failed"):
            # same file name as the existing document
            api_client_for(api_user).post(
                list_url(member.pk), payload(), format="multipart"
            )

    assert before <= files_in(storage)
    assert storage.exists(existing.document.name)
    assert Document.objects.get() == existing
    if not allow_overwrite:
        # Django gave the upload another name
        with storage.open(existing.document.name) as stored:
            assert stored.read() == b"existing content"
        assert Document.objects.get().content_hash_ok


@pytest.mark.django_db
def test_same_file_can_be_uploaded_twice(api_client, member, payload, stem):
    first = api_client.post(list_url(member.pk), payload(), format="multipart")
    second = api_client.post(list_url(member.pk), payload(), format="multipart")

    assert first.status_code == second.status_code == 201
    first, second = first.json(), second.json()
    assert first["id"] != second["id"]
    assert first["content_hash"] == second["content_hash"]
    assert first["filename"] != second["filename"]
    assert Document.objects.filter(member=member).count() == 2
    assert len(stored_files(stem)) == 2


@pytest.mark.django_db
def test_uploaded_document_shows_up_in_office(
    api_client, logged_in_client, configuration, member, payload
):
    response = api_client.post(
        list_url(member.pk),
        payload(title="Uploaded through the API", date=None),
        format="multipart",
    )
    assert response.status_code == 201

    for name in ("members.documents", "members.timeline", "members.log"):
        response = logged_in_client.get(
            reverse(f"office:{name}", kwargs={"pk": member.pk})
        )
        assert response.status_code == 200, name
    response = logged_in_client.get(
        reverse("office:members.documents", kwargs={"pk": member.pk})
    )
    assert "Uploaded through the API" in response.content.decode()


@pytest.fixture
def legacy_document(member, create_document):
    """What the model allows and older or plugin-made documents can contain."""
    return create_document(
        member, title=None, date=None, category="retired.plugin.category"
    )


@pytest.mark.django_db
def test_legacy_document_is_returned_as_stored(api_client, member, legacy_document):
    expected = {
        "id": legacy_document.pk,
        "title": None,
        "date": None,
        "category": "retired.plugin.category",
        "direction": "outgoing",
        "content_hash": legacy_document.content_hash,
        "filename": legacy_document.basename,
    }

    response = api_client.get(list_url(member.pk))
    assert response.status_code == 200
    assert response.json()["results"] == [expected]

    response = api_client.get(detail_url(member.pk, legacy_document.pk))
    assert response.status_code == 200
    assert response.json() == expected


@pytest.fixture
def schema():
    response = APIClient().get(reverse("api:schema"), {"format": "json"})
    assert response.status_code == 200
    return json.loads(response.content)


def resolve(schema, node):
    """Follow references, also the ``allOf`` wrapper around a single one."""
    while "$ref" in node or "allOf" in node:
        if "allOf" in node:
            (node,) = node["allOf"]
        else:
            node = schema["components"]["schemas"][node["$ref"].rsplit("/", 1)[-1]]
    return node


def component(schema, name):
    return schema["components"]["schemas"][name]


def refers_to(schema, node, name):
    return resolve(schema, node) is component(schema, name)


@pytest.mark.django_db
def test_schema_describes_multipart_upload(schema):
    operations = schema["paths"]["/api/v1/members/{member_pk}/documents/"]
    assert set(operations) == {"get", "post"}

    content = operations["post"]["requestBody"]["content"]
    assert list(content) == ["multipart/form-data"]
    assert operations["post"]["requestBody"]["required"] is True
    assert refers_to(schema, content["multipart/form-data"]["schema"], "DocumentUpload")

    upload = component(schema, "DocumentUpload")
    properties = upload["properties"]
    assert set(properties) == {"document", "title", "date", "category", "direction"}
    assert properties["document"] == {"type": "string", "format": "binary"}
    assert set(upload["required"]) == {"document", "title"}
    assert properties["title"] == {"type": "string", "maxLength": 300}
    assert properties["date"] == {"type": "string", "format": "date"}
    assert properties["category"]["default"] == "byro.documents.misc"
    categories = resolve(schema, properties["category"])["enum"]
    assert "byro.documents.misc" in categories
    assert "byro.bookkeeping.receipt" in categories
    assert set(resolve(schema, properties["direction"])["enum"]) == {
        "incoming",
        "outgoing",
        "other",
    }
    # nothing in a new upload may be null
    assert not any(
        "nullable" in node or "nullable" in resolve(schema, node)
        for node in properties.values()
    )

    created = operations["post"]["responses"]["201"]["content"]["application/json"]
    assert refers_to(schema, created["schema"], "Document")


@pytest.mark.django_db
def test_schema_describes_stored_documents(schema):
    """The response describes every stored document, not only what an upload
    through the API can create."""
    document = component(schema, "Document")
    properties = document["properties"]
    assert set(properties) == RESPONSE_FIELDS
    assert set(document["required"]) == RESPONSE_FIELDS
    assert all(node["readOnly"] is True for node in properties.values())
    for name in ("title", "date", "category", "content_hash"):
        assert properties[name]["nullable"] is True, name
    for name in ("id", "direction", "filename"):
        assert "nullable" not in properties[name], name
    # a category can come from a plugin that is no longer installed
    assert properties["category"]["type"] == "string"
    assert "enum" not in resolve(schema, properties["category"])
    assert properties["date"]["format"] == "date"
    assert set(resolve(schema, properties["direction"])["enum"]) == {
        "incoming",
        "outgoing",
        "other",
    }


def assert_matches_document_schema(schema, data):
    document = component(schema, "Document")
    assert set(data) == set(document["properties"])
    for name, value in data.items():
        node = document["properties"][name]
        if value is None:
            assert node.get("nullable") is True, name
            continue
        node = resolve(schema, node)
        expected_type = {"string": str, "integer": int}[node["type"]]
        assert isinstance(value, expected_type), name
        if "enum" in node:
            assert value in node["enum"], name
        if "maxLength" in node:
            assert len(value) <= node["maxLength"], name
        if node.get("format") == "date":
            datetime.date.fromisoformat(value)


@pytest.mark.django_db
def test_responses_match_the_schema(
    schema, api_client, member, legacy_document, payload
):
    response = api_client.post(list_url(member.pk), payload(), format="multipart")
    assert response.status_code == 201
    assert_matches_document_schema(schema, response.json())

    response = api_client.get(detail_url(member.pk, legacy_document.pk))
    assert_matches_document_schema(schema, response.json())

    response = api_client.get(list_url(member.pk))
    assert response.json()["count"] == 2
    for entry in response.json()["results"]:
        assert_matches_document_schema(schema, entry)


@pytest.mark.django_db
def test_schema_describes_list_and_detail(schema):
    documents = schema["paths"]["/api/v1/members/{member_pk}/documents/"]
    listing = documents["get"]["responses"]["200"]["content"]["application/json"]
    page = resolve(schema, listing["schema"])
    assert {"count", "results"} <= set(page["properties"])
    assert refers_to(schema, page["properties"]["results"]["items"], "Document")
    assert "requestBody" not in documents["get"]

    detail = schema["paths"]["/api/v1/members/{member_pk}/documents/{id}/"]
    assert set(detail) == {"get"}
    found = detail["get"]["responses"]["200"]["content"]["application/json"]
    assert refers_to(schema, found["schema"], "Document")
    parameters = {p["name"]: p for p in detail["get"]["parameters"]}
    assert set(parameters) == {"member_pk", "id"}
    assert all(p["in"] == "path" for p in parameters.values())
    assert all(p["schema"]["type"] == "integer" for p in parameters.values())
