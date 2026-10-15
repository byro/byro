"""Storage of document files.

Migrations refer to the names in this module, so they have to stay
importable here. The module must not import ``byro.documents.models``.
"""

import os
import uuid

from django.db import models
from django.db.models.fields.files import FieldFile

#: All document files are stored below this directory of the storage.
DOCUMENT_STORAGE_PREFIX = "documents"
FILENAME_MAX_LENGTH = 255


def clean_filename(name):
    """Reduce the name a file was handed to byro with to a plain base name."""
    name = str(name or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(character for character in name if character.isprintable())
    name = name.strip()
    if name in ("", ".", ".."):
        return ""
    if len(name) > FILENAME_MAX_LENGTH:
        root, extension = os.path.splitext(name)
        if len(extension) >= FILENAME_MAX_LENGTH:
            extension = ""
        name = root[: FILENAME_MAX_LENGTH - len(extension)] + extension
    return name


def document_storage_key(instance, filename):
    """A new storage key for every file that is written.

    The key depends on nothing about the file or the document, so two writes
    never use the same key, whatever the storage does with existing names.
    """
    token = uuid.uuid4().hex
    return f"{DOCUMENT_STORAGE_PREFIX}/{token[:2]}/{token}"


class DocumentFieldFile(FieldFile):
    def save(self, name, content, save=True):
        super().save(name, content, save=False)
        # Only reached when the storage accepted the file: key, file name and
        # hash of the document change together or not at all.
        self.instance.filename = clean_filename(name)
        self.instance.content_hash = None
        if save:
            self.instance.save()

    save.alters_data = True


class DocumentFileField(models.FileField):
    attr_class = DocumentFieldFile
