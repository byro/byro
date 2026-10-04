"""``documents.0005`` changes the default of ``Document.date`` from a datetime
to a date. It must stay a pure schema migration: there is no date that could
be made up for an existing document without one. Like the currency tests,
this runs the real ``migrate`` command against an SQLite database of its own.
"""

from django.db import migrations
from django.db.migrations.loader import MigrationLoader
from django.utils.timezone import localdate
from test_currency_default_migration import migrate, query

BEFORE = ("documents", "0004_auto_20181013_1611")
MIGRATION = ("documents", "0005_document_date_default")

DOCUMENTS = "SELECT id, document, date, title FROM documents_document ORDER BY id"


def test_migration_only_changes_the_field():
    migration = MigrationLoader(None).get_migration(*MIGRATION)

    assert [type(operation) for operation in migration.operations] == [
        migrations.AlterField
    ]
    (operation,) = migration.operations
    assert (operation.model_name, operation.name) == ("document", "date")
    assert operation.field.null is True
    assert operation.field.default is localdate


def test_existing_documents_keep_their_date_or_none(tmp_path):
    database = tmp_path / "db.sqlite3"
    migrate(database, *BEFORE)
    for name, date in (("undated.pdf", None), ("dated.pdf", "2020-05-17")):
        query(
            database,
            "INSERT INTO documents_document (document, date, title, direction)"
            " VALUES (?, ?, ?, 'incoming')",
            f"documents/2020/05/{name}",
            date,
            name,
        )
    expected = [
        (1, "documents/2020/05/undated.pdf", None, "undated.pdf"),
        (2, "documents/2020/05/dated.pdf", "2020-05-17", "dated.pdf"),
    ]
    assert query(database, DOCUMENTS) == expected

    migrate(database)

    assert query(database, DOCUMENTS) == expected
