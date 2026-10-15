from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now

from byro.documents.fields import DOCUMENT_STORAGE_PREFIX
from byro.documents.models import Document


def walk(storage, directory):
    directories, files = storage.listdir(directory)
    for name in files:
        yield f"{directory}/{name}"
    for name in directories:
        yield from walk(storage, f"{directory}/{name}")


class Command(BaseCommand):
    help = (
        "List the files in the document storage that no document refers to. "
        "Nothing is changed or deleted."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-age-hours",
            type=float,
            default=24,
            help=(
                "Only report files older than this (default: 24), so that "
                "uploads that are still being saved are not reported."
            ),
        )

    def handle(self, *args, min_age_hours, **options):
        if min_age_hours < 0:
            raise CommandError("--min-age-hours must not be negative.")
        storage = Document._meta.get_field("document").storage

        # List the files first and read the references afterwards: a file
        # whose document is saved in between counts as referenced.
        try:
            keys = sorted(walk(storage, DOCUMENT_STORAGE_PREFIX))
        except FileNotFoundError:
            keys = []
        except NotImplementedError:
            raise CommandError(
                "The document storage cannot list its files, so files without "
                "a document cannot be found."
            )
        referenced = set(
            Document.objects.exclude(document="").values_list("document", flat=True)
        )
        cutoff = now() - timedelta(hours=min_age_hours)

        orphans = []
        too_recent = 0
        for key in keys:
            if key in referenced:
                continue
            try:
                modified = storage.get_modified_time(key)
            except NotImplementedError:
                raise CommandError(
                    "The document storage cannot tell when its files were "
                    "changed, so files without a document cannot be judged."
                )
            if modified > cutoff:
                too_recent += 1
                continue
            orphans.append((key, storage.size(key), modified))

        for key, size, modified in orphans:
            self.stdout.write(f"{key}\t{size}\t{modified.isoformat()}")
        self.stdout.write(
            f"{len(keys)} files checked: {len(keys) - len(orphans) - too_recent} "
            f"referenced by a document, {too_recent} too recent to judge, "
            f"{len(orphans)} without a document."
        )
