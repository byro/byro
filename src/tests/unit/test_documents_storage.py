import re
from hashlib import sha512

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError, connection, models, transaction

from byro.common.models import LogEntry
from byro.documents.fields import (
    DOCUMENT_STORAGE_PREFIX,
    clean_filename,
    document_storage_key,
)
from byro.documents.management.commands.list_orphaned_documents import walk
from byro.documents.models import Document, get_document_category_names

KEY = re.compile(r"^documents/(?P<shard>[0-9a-f]{2})/(?P<token>[0-9a-f]{32})$")


def digest(content):
    return f"sha512:{sha512(content).hexdigest()}"


def stored_entries(document):
    return LogEntry.objects.filter(
        content_object=document, action_type="byro.documents.document.stored"
    ).count()


def read(storage, key):
    with storage.open(key, "rb") as handle:
        return handle.read()


def files_in(storage):
    try:
        return set(walk(storage, DOCUMENT_STORAGE_PREFIX))
    except FileNotFoundError:
        return set()


def unreferenced_leftovers(storage, before):
    """The files added since ``before``. None of the earlier files is gone,
    and no document refers to the added ones."""
    after = files_in(storage)
    assert before <= after
    leftovers = after - before
    assert not Document.objects.filter(document__in=leftovers).exists()
    return leftovers


class FailingStorage(InMemoryStorage):
    """Fails on request, before or after the data reached the storage."""

    fail = None

    def _save(self, name, content):
        if self.fail == "before":
            raise OSError("the storage is not available")
        name = super()._save(name, content)
        if self.fail == "after":
            raise OSError("the storage failed after writing")
        return name


STORAGES = {
    "filesystem": lambda path: FileSystemStorage(location=path),
    "overwriting": lambda path: FileSystemStorage(location=path, allow_overwrite=True),
    "memory": lambda path: InMemoryStorage(),
}


@pytest.fixture(params=STORAGES)
def storage(request, use_document_storage, tmp_path):
    return use_document_storage(STORAGES[request.param](tmp_path))


@pytest.fixture
def failing_storage(use_document_storage):
    return use_document_storage(FailingStorage())


@pytest.mark.django_db
def test_files_with_the_same_name_get_independent_keys(storage):
    first = Document.objects.create(
        document=SimpleUploadedFile("scan 0042.pdf", b"first"), title="First"
    )
    second = Document.objects.create(
        document=SimpleUploadedFile("scan 0042.pdf", b"second"), title="Second"
    )
    first.refresh_from_db()
    second.refresh_from_db()

    for document in (first, second):
        match = KEY.match(document.document.name)
        assert match, document.document.name
        assert match["shard"] == match["token"][:2]
        assert "scan" not in document.document.name
        assert document.filename == "scan 0042.pdf"
    assert first.document.name != second.document.name
    assert files_in(storage) == {first.document.name, second.document.name}
    # the first file is untouched, also on a storage that overwrites
    assert read(storage, first.document.name) == b"first"
    assert first.content_hash == digest(b"first")
    assert first.content_hash_ok
    assert read(storage, second.document.name) == b"second"
    assert second.content_hash == digest(b"second")


def test_storage_key_ignores_the_file_name_and_is_new_every_time():
    keys = {document_storage_key(None, "scan.pdf") for _ in range(100)}

    assert len(keys) == 100
    assert all(KEY.match(key) for key in keys)


@pytest.mark.django_db
def test_second_write_gets_a_new_key_and_leaves_the_old_file(storage):
    document = Document.objects.create(
        document=SimpleUploadedFile("application.pdf", b"first"), title="Application"
    )
    old_key = document.document.name

    document.document.save("application-signed.pdf", ContentFile(b"second"))
    document.refresh_from_db()

    assert document.document.name != old_key
    assert KEY.match(document.document.name)
    assert document.filename == "application-signed.pdf"
    assert document.content_hash == digest(b"second")
    assert document.content_hash_ok
    assert stored_entries(document) == 2
    # the old file is still there and nothing refers to it any more
    assert read(storage, old_key) == b"first"
    assert not Document.objects.filter(document=old_key).exists()


@pytest.mark.django_db
def test_write_without_saving_changes_the_database_only_on_a_full_save():
    document = Document.objects.create(
        document=SimpleUploadedFile("application.pdf", b"first"), title="Application"
    )
    old_key = document.document.name

    document.document.save("second.pdf", ContentFile(b"second"), save=False)
    assert (document.filename, document.content_hash) == ("second.pdf", None)
    stored = Document.objects.get(pk=document.pk)
    assert (stored.document.name, stored.filename) == (old_key, "application.pdf")
    assert stored.content_hash == digest(b"first")

    # a partial save without the file leaves file, name and hash alone
    document.title = "Signed application"
    document.save(update_fields=["title"])
    stored = Document.objects.get(pk=document.pk)
    assert stored.title == "Signed application"
    assert (stored.document.name, stored.filename) == (old_key, "application.pdf")
    assert stored.content_hash == digest(b"first")
    assert stored_entries(document) == 1

    document.save()
    stored = Document.objects.get(pk=document.pk)
    assert stored.document.name == document.document.name != old_key
    assert stored.filename == "second.pdf"
    assert stored.content_hash == digest(b"second")
    assert stored_entries(document) == 2


@pytest.mark.django_db
def test_partial_save_with_the_file_saves_name_and_hash_as_well():
    document = Document.objects.create(
        document=SimpleUploadedFile("application.pdf", b"first"), title="Application"
    )

    document.document.save("second.pdf", ContentFile(b"second"), save=False)
    document.save(update_fields=["document"])

    stored = Document.objects.get(pk=document.pk)
    assert stored.document.name == document.document.name
    assert stored.filename == "second.pdf"
    assert stored.content_hash == digest(b"second")


@pytest.mark.django_db
def test_partial_save_does_not_add_a_hash_to_an_old_document():
    document = Document.objects.create(
        document=SimpleUploadedFile("application.pdf", b"first"), title="Application"
    )
    Document.objects.filter(pk=document.pk).update(content_hash=None)
    document.refresh_from_db()

    document.title = "Changed"
    document.save(update_fields=["title"])
    assert Document.objects.get(pk=document.pk).content_hash is None

    document.save()
    assert Document.objects.get(pk=document.pk).content_hash == digest(b"first")


@pytest.mark.parametrize("fail", ("before", "after"))
@pytest.mark.django_db
def test_failed_second_write_changes_nothing(failing_storage, fail):
    document = Document.objects.create(
        document=SimpleUploadedFile("application.pdf", b"first"), title="Application"
    )
    state = (document.document.name, document.filename, document.content_hash)
    files = files_in(failing_storage)

    failing_storage.fail = fail
    with pytest.raises(OSError):
        document.document.save("second.pdf", ContentFile(b"second"))
    failing_storage.fail = None

    current = (document.document.name, document.filename, document.content_hash)
    assert current == state
    stored = Document.objects.get(pk=document.pk)
    assert (stored.document.name, stored.filename, stored.content_hash) == state

    # saving the instance afterwards does not change anything either
    document.save()
    stored = Document.objects.get(pk=document.pk)
    assert (stored.document.name, stored.filename, stored.content_hash) == state
    assert stored_entries(document) == 1
    assert read(failing_storage, state[0]) == b"first"
    # a file the storage wrote before failing stays behind, unreferenced
    leftovers = unreferenced_leftovers(failing_storage, files)
    assert len(leftovers) == (1 if fail == "after" else 0)


@pytest.mark.parametrize("fail", ("before", "after"))
@pytest.mark.django_db
def test_failed_first_write_creates_nothing(failing_storage, fail):
    document = Document(
        document=SimpleUploadedFile("application.pdf", b"first"), title="New"
    )

    failing_storage.fail = fail
    with pytest.raises(OSError):
        document.save()
    failing_storage.fail = None

    assert not Document.objects.exists()
    assert (document.filename, document.content_hash) == ("", None)

    document.save()
    document.refresh_from_db()
    assert KEY.match(document.document.name)
    assert document.filename == "application.pdf"
    assert document.content_hash == digest(b"first")
    assert stored_entries(document) == 1


@pytest.mark.django_db
def test_file_name_and_key_are_set_before_the_row_is_written(monkeypatch):
    # The order of the model fields must not matter: Document.save() stores
    # the file before Django reads the values of the row.
    seen = []
    model_save = models.Model.save

    def spy(self, *args, **kwargs):
        if isinstance(self, Document) and not seen:
            seen.append((self.filename, self.document.name, self.content_hash))
        return model_save(self, *args, **kwargs)

    monkeypatch.setattr(models.Model, "save", spy)

    Document.objects.create(
        document=SimpleUploadedFile("scan 0042.pdf", b"first"), title="T"
    )

    filename, key, content_hash = seen[0]
    assert filename == "scan 0042.pdf"
    assert KEY.match(key)
    assert content_hash is None


@pytest.mark.django_db
def test_file_added_after_the_document_was_created(storage):
    # how plugins create documents: the row first, then the file
    document = Document.objects.create(title="Donation receipt 2023", category="x")
    assert (document.filename, document.content_hash) == ("", None)
    assert stored_entries(document) == 0

    document.document.save(
        "receipts/receipt_2023_4711_Jona Than.pdf", ContentFile(b"receipt")
    )
    document.refresh_from_db()

    assert KEY.match(document.document.name)
    assert "4711" not in document.document.name
    assert document.filename == "receipt_2023_4711_Jona Than.pdf"
    assert document.content_hash == digest(b"receipt")
    assert stored_entries(document) == 1


@pytest.mark.parametrize(
    "name,expected",
    (
        ("scan 0042.pdf", "scan 0042.pdf"),
        ("Aufnahmeantrag Müller.pdf", "Aufnahmeantrag Müller.pdf"),
        ("C:\\Users\\jona\\scan.pdf", "scan.pdf"),
        ("../../etc/passwd", "passwd"),
        ("receipts/2023/receipt.pdf", "receipt.pdf"),
        ("line\nbreak.pdf", "linebreak.pdf"),
        ("  padded.pdf  ", "padded.pdf"),
        ("..", ""),
        (".", ""),
        ("", ""),
        (None, ""),
    ),
)
def test_clean_filename(name, expected):
    assert clean_filename(name) == expected


def test_clean_filename_shortens_before_the_extension():
    name = clean_filename("a" * 300 + ".pdf")

    assert len(name) == 255
    assert name.endswith("a.pdf")


REGISTRATION_FORM = "byro.documents.registration_form"


@pytest.mark.parametrize(
    "title,category,filename,expected",
    (
        pytest.param(
            "Aufnahmeantrag Max Müller",
            REGISTRATION_FORM,
            "scan0042.pdf",
            "Aufnahmeantrag Max Müller.pdf",
            id="title",
        ),
        pytest.param(
            "Antrag.pdf", None, "scan.pdf", "Antrag.pdf", id="title-ends-in-extension"
        ),
        pytest.param(
            "Antrag.PDF", None, "scan.pdf", "Antrag.PDF", id="extension-in-other-case"
        ),
        pytest.param(
            "Antrag", None, "scan.PDF", "Antrag.PDF", id="extension-kept-as-is"
        ),
        pytest.param("Antrag", None, "scan", "Antrag", id="no-extension"),
        pytest.param("Antrag", None, "scan.", "Antrag", id="empty-extension"),
        pytest.param(
            'a/b:c*?"<>|', None, "x.txt", "a_b_c______.txt", id="unsafe-characters"
        ),
        pytest.param(
            "Line\nbreak\ttab",
            None,
            "x.txt",
            "Line break tab.txt",
            id="control-characters",
        ),
        pytest.param(" .hidden. ", None, "x.pdf", "hidden.pdf", id="dots-and-spaces"),
        pytest.param("x" * 200, None, "x.pdf", "x" * 150 + ".pdf", id="long-title"),
        pytest.param(
            None,
            "retired.plugin.category",
            "scan.pdf",
            "scan.pdf",
            id="unknown-category",
        ),
        pytest.param(None, None, "scan 0042.pdf", "scan 0042.pdf", id="filename"),
        pytest.param(
            "   ", None, 'scan:"x".pdf', "scan__x_.pdf", id="filename-cleaned"
        ),
    ),
)
@pytest.mark.django_db
def test_download_filename(title, category, filename, expected):
    document = Document(title=title, category=category, filename=filename)

    assert document.download_filename == expected


@pytest.mark.django_db
def test_download_filename_falls_back_to_the_category_name():
    document = Document(title=None, category=REGISTRATION_FORM, filename="scan.pdf")

    # the display name in the active language, never the key
    name = str(get_document_category_names()[REGISTRATION_FORM])
    assert document.download_filename == f"{name}.pdf"
    assert REGISTRATION_FORM not in document.download_filename


@pytest.mark.django_db
def test_download_filename_without_any_name():
    document = Document.objects.create(title=None, category=None)

    assert document.download_filename == f"document-{document.pk}"
    assert Document(title=None).download_filename == "document"


@pytest.mark.django_db
def test_basename_is_the_file_name():
    document = Document.objects.create(
        document=SimpleUploadedFile("scan.pdf", b"x"), title="T"
    )

    assert document.basename == "scan.pdf"


@pytest.mark.django_db
def test_reading_works_with_handles_that_cannot_be_reopened(non_reopenable_storage):
    document = Document.objects.create(
        document=SimpleUploadedFile("letter.pdf", b"%PDF-1.4 letter"), title="T"
    )
    document = Document.objects.get(pk=document.pk)

    # both read the file through the same instance
    assert document.content_hash_ok
    assert document.mime_type_guessed == "application/pdf"
    with document.open_file() as handle:
        assert handle.read() == b"%PDF-1.4 letter"


@pytest.mark.django_db
def test_outer_rollback_leaves_existing_files_alone(storage):
    existing = Document.objects.create(
        document=SimpleUploadedFile("scan 0042.pdf", b"existing"), title="Existing"
    )
    before = files_in(storage)

    with transaction.atomic():
        Document.objects.create(
            document=SimpleUploadedFile("scan 0042.pdf", b"new"), title="New"
        )
        transaction.set_rollback(True)

    assert list(Document.objects.all()) == [existing]
    assert read(storage, existing.document.name) == b"existing"
    # at most the new file stays behind, and nothing refers to it
    assert len(unreferenced_leftovers(storage, before)) <= 1


@pytest.mark.django_db(transaction=True)
def test_failed_commit_leaves_existing_files_alone(storage, monkeypatch):
    existing = Document.objects.create(
        document=SimpleUploadedFile("scan 0042.pdf", b"existing"), title="Existing"
    )
    before = files_in(storage)

    def commit():
        raise OperationalError("the commit failed")

    with monkeypatch.context() as patch:
        patch.setattr(connection, "commit", commit)
        with pytest.raises(OperationalError, match="the commit failed"):
            Document.objects.create(
                document=SimpleUploadedFile("scan 0042.pdf", b"new"), title="New"
            )

    assert list(Document.objects.all()) == [existing]
    assert read(storage, existing.document.name) == b"existing"
    assert len(unreferenced_leftovers(storage, before)) == 1
