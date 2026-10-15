from django.db import migrations

BATCH_SIZE = 500


def fill_filename(apps, schema_editor):
    """Documents from before the file name was recorded get the last part of
    their storage key, the best name there is. The storage is not touched."""
    Document = apps.get_model("documents", "Document")
    documents = (
        Document.objects.filter(filename="")
        .exclude(document="")
        .values_list("pk", "document")
    )
    batch = []
    for pk, key in documents.iterator(chunk_size=BATCH_SIZE):
        name = key.replace("\\", "/").rsplit("/", 1)[-1][:255]
        batch.append(Document(pk=pk, filename=name))
        if len(batch) == BATCH_SIZE:
            Document.objects.bulk_update(batch, ["filename"])
            batch = []
    if batch:
        Document.objects.bulk_update(batch, ["filename"])


class Migration(migrations.Migration):
    dependencies = [("documents", "0006_document_filename")]

    operations = [migrations.RunPython(fill_filename, migrations.RunPython.noop)]
