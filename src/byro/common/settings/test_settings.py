import atexit
import os
import tempfile
from contextlib import suppress

from byro.settings import *  # noqa

tmpdir = tempfile.TemporaryDirectory()
os.environ.setdefault("DATA_DIR", tmpdir.name)


BASE_DIR = tmpdir.name
DATA_DIR = tmpdir.name
LOG_DIR = os.path.join(DATA_DIR, "logs")
MEDIA_ROOT = os.path.join(DATA_DIR, "media")
STATIC_ROOT = os.path.join(DATA_DIR, "static")
HTMLEXPORT_ROOT = os.path.join(DATA_DIR, "htmlexport")

for directory in (BASE_DIR, DATA_DIR, LOG_DIR, MEDIA_ROOT, HTMLEXPORT_ROOT):
    os.makedirs(directory, exist_ok=True)

atexit.register(tmpdir.cleanup)

EMAIL_BACKEND = "django.core.mail.outbox"
MAIL_FROM = "orga@orga.org"

COMPRESS_ENABLED = COMPRESS_OFFLINE = False
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
GET_SOLO_TEMPLATE_TAG_NAME = "get_solo"

DEBUG = True
DEBUG_PROPAGATE_EXCEPTIONS = True

with suppress(ValueError):
    INSTALLED_APPS.remove("debug_toolbar.apps.DebugToolbarConfig")  # noqa
    MIDDLEWARE.remove("debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa
