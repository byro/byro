"""``documents.0006`` switches new files to keys of their own and adds the
``filename`` field, ``documents.0007`` fills it for existing documents. Like
the other migration tests, this runs the real ``migrate`` command in a fresh
interpreter against an SQLite database of its own.
"""

import importlib
import inspect

from django.db.migrations.loader import MigrationLoader
from test_currency_default_migration import migrate, query

from byro.documents.fields import DocumentFileField, document_storage_key

BEFORE = ("documents", "0005_document_date_default")
MIGRATIONS = ("0006_document_filename", "0007_document_filename_data")

DOCUMENTS = "SELECT id, document, filename FROM documents_document ORDER BY id"


def test_existing_documents_keep_their_key_and_get_a_file_name(tmp_path):
    database = tmp_path / "db.sqlite3"
    migrate(database, *BEFORE)
    # the files do not exist: the migration must not need them
    for key in (
        "documents/2020/05/scan 0042.pdf",
        "documents/2021/01/receipts/receipt_2021_AbC1234.pdf",
        "",
    ):
        query(
            database,
            "INSERT INTO documents_document (document, title, direction)"
            " VALUES (?, 'Old', 'incoming')",
            key,
        )

    migrate(database)

    assert query(database, DOCUMENTS) == [
        (1, "documents/2020/05/scan 0042.pdf", "scan 0042.pdf"),
        (
            2,
            "documents/2021/01/receipts/receipt_2021_AbC1234.pdf",
            "receipt_2021_AbC1234.pdf",
        ),
        (3, "", ""),
    ]


def test_migrations_do_not_depend_on_the_current_model():
    for name in MIGRATIONS:
        module = importlib.import_module(f"byro.documents.migrations.{name}")
        assert "byro.documents.models" not in inspect.getsource(module), name


def test_migration_refers_to_the_stable_field_module():
    migration = MigrationLoader(None).get_migration("documents", MIGRATIONS[0])
    (field,) = [
        operation.field
        for operation in migration.operations
        if getattr(operation, "name", None) == "document"
    ]

    assert type(field) is DocumentFileField
    assert field.upload_to is document_storage_key
    assert field.deconstruct()[1] == "byro.documents.fields.DocumentFileField"
