import datetime
from io import StringIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, InMemoryStorage, Storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.utils.timezone import now

from byro.documents.management.commands.list_orphaned_documents import walk
from byro.documents.models import Document

OLD = now() - datetime.timedelta(days=3)


class AgedStorage(FileSystemStorage):
    """Reports a fixed age for the files the test marks as old."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old = set()

    def get_modified_time(self, name):
        return OLD if name in self.old else now()


class UnlistableStorage(InMemoryStorage):
    def listdir(self, path):
        return Storage.listdir(self, path)


class TimelessStorage(InMemoryStorage):
    def get_modified_time(self, name):
        return Storage.get_modified_time(self, name)


@pytest.fixture
def storage(use_document_storage, tmp_path):
    return use_document_storage(AgedStorage(location=tmp_path))


def run(*args):
    out = StringIO()
    call_command("list_orphaned_documents", *args, stdout=out)
    return out.getvalue().splitlines()


def contents(storage):
    return {key: storage.open(key).read() for key in walk(storage, "documents")}


@pytest.mark.django_db
def test_lists_only_old_files_without_a_document(storage):
    document = Document.objects.create(
        document=SimpleUploadedFile("kept.pdf", b"kept"), title="Kept"
    )
    replaced = document.document.name
    document.document.save("second.pdf", ContentFile(b"second"))
    legacy = storage.save("documents/2020/05/legacy scan.pdf", ContentFile(b"old"))
    Document.objects.create(title="Legacy", document=legacy)
    orphan_legacy = storage.save("documents/2019/01/lost.pdf", ContentFile(b"lost"))
    leftover = storage.save("documents/ab/" + "ab" * 16, ContentFile(b"leftover"))
    recent = storage.save("documents/cd/" + "cd" * 16, ContentFile(b"recent"))
    storage.old |= {replaced, legacy, orphan_legacy, leftover, document.document.name}
    before = contents(storage)
    assert recent in before

    lines = run()

    reported = {line.split("\t")[0]: line.split("\t")[1:] for line in lines[:-1]}
    assert list(reported) == sorted([replaced, orphan_legacy, leftover])
    assert reported[leftover] == [str(len(b"leftover")), OLD.isoformat()]
    assert lines[-1] == (
        "6 files checked: 2 referenced by a document, 1 too recent to judge, "
        "3 without a document."
    )
    # nothing was changed or deleted
    assert contents(storage) == before


@pytest.mark.django_db
def test_grace_period_can_be_changed(storage):
    # three days old
    leftover = storage.save("documents/ab/" + "ab" * 16, ContentFile(b"leftover"))
    storage.old.add(leftover)

    assert run()[0].startswith(leftover)
    assert run("--min-age-hours", "100")[-1].endswith(
        "1 too recent to judge, 0 without a document."
    )


@pytest.mark.django_db
def test_empty_storage(storage):
    assert run() == [
        "0 files checked: 0 referenced by a document, 0 too recent to judge, "
        "0 without a document."
    ]


@pytest.mark.parametrize(
    "storage_class,message",
    (
        (UnlistableStorage, "cannot list its files"),
        (TimelessStorage, "cannot tell when its files were changed"),
    ),
)
@pytest.mark.django_db
def test_stops_when_the_storage_cannot_answer(
    use_document_storage, storage_class, message
):
    storage = use_document_storage(storage_class())
    storage.save("documents/ab/" + "ab" * 16, ContentFile(b"leftover"))

    with pytest.raises(CommandError, match=message):
        run()


@pytest.mark.django_db
def test_negative_grace_period(storage):
    with pytest.raises(CommandError, match="must not be negative"):
        run("--min-age-hours", "-1")
