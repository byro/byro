"""Creation of the on-disk ``SECRET_KEY`` file.

When no ``[site] secret`` is configured, byro keeps an auto-generated Django
``SECRET_KEY`` in ``<DATA_DIR>/.secret``. Losing or corrupting that file
invalidates all sessions and every MFA device (TOTP secrets are encrypted with
a key derived from it). Two properties therefore matter here:

* Processes that start at the same time (gunicorn workers, ``web`` and
  ``periodic`` containers) must agree on one value: the first published secret
  wins, everybody else reads it.
* A crash while writing must never leave an empty or half-written ``.secret``
  behind that would later be treated as a valid secret.

Both are achieved by writing the complete secret to a temporary file in the
same directory and publishing it atomically with :func:`os.link`, which fails
if the target already exists.
"""

import os
import tempfile

from django.utils.crypto import get_random_string

SECRET_LENGTH = 50
SECRET_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"


def _read_secret(path):
    """Return the stripped file content, ``""`` for an empty file and ``None``
    if the file does not exist."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def _write_temp_secret(directory, secret):
    """Write ``secret`` completely (fsync'ed, mode 0600) to a new temporary
    file in ``directory`` and return its path."""
    fd, tmp_path = tempfile.mkstemp(prefix=".secret.", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        if hasattr(os, "fchown"):
            os.fchown(fd, os.getuid(), os.getgid())
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(secret)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        _unlink_quietly(tmp_path)
        raise
    return tmp_path


def _unlink_quietly(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def _publish(tmp_path, path):
    """Atomically make ``tmp_path`` visible as ``path``.

    Returns ``True`` if our file was published, ``False`` if ``path`` already
    existed (a concurrent process won). Uses a hard link because, unlike
    ``rename``, it never overwrites an existing target.
    """
    try:
        os.link(tmp_path, path)
        return True
    except FileExistsError:
        return False
    except OSError:
        # Filesystems without hard links: fall back to rename, guarded by an
        # existence check. Not fully race-free, but only reached on exotic
        # mounts where ``link`` is unavailable.
        if os.path.exists(path):
            return False
        os.replace(tmp_path, path)
        return True


def get_or_create_secret(path):
    """Return the secret stored in ``path``, creating it atomically if needed.

    An existing non-empty file always wins. An existing *empty* file is not a
    valid secret (it can only be the leftover of an interrupted write by an
    older byro version) and is replaced.
    """
    existing = _read_secret(path)
    if existing:
        return existing

    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    secret = get_random_string(SECRET_LENGTH, SECRET_CHARS)
    tmp_path = _write_temp_secret(directory, secret)
    try:
        if existing is None and _publish(tmp_path, path):
            return secret

        # Either the file existed (possibly empty) before we started, or a
        # concurrent process published one in the meantime.
        winner = _read_secret(path)
        if winner:
            return winner
        # The file exists but is empty: replace the invalid leftover.
        os.replace(tmp_path, path)
        return secret
    finally:
        _unlink_quietly(tmp_path)
