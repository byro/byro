import multiprocessing
import os
import stat

import pytest

from byro.common.settings import secret as secret_module
from byro.common.settings.secret import SECRET_LENGTH, get_or_create_secret


def _no_leftovers(directory):
    return [name for name in os.listdir(directory) if name.startswith(".secret.")]


def test_creates_secret_file_with_restrictive_mode(tmp_path):
    path = tmp_path / ".secret"

    value = get_or_create_secret(str(path))

    assert len(value) == SECRET_LENGTH
    assert path.read_text(encoding="utf-8") == value
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert _no_leftovers(tmp_path) == []


def test_second_call_returns_same_secret(tmp_path):
    path = tmp_path / ".secret"

    first = get_or_create_secret(str(path))
    second = get_or_create_secret(str(path))

    assert first == second


def test_existing_secret_wins(tmp_path):
    path = tmp_path / ".secret"
    path.write_text("  pre-existing-secret \n", encoding="utf-8")

    assert get_or_create_secret(str(path)) == "pre-existing-secret"
    assert path.read_text(encoding="utf-8") == "  pre-existing-secret \n"


def test_creates_missing_parent_directory(tmp_path):
    path = tmp_path / "nested" / "data" / ".secret"

    value = get_or_create_secret(str(path))

    assert path.read_text(encoding="utf-8") == value


def test_concurrent_writer_wins_when_publishing(tmp_path, monkeypatch):
    """A secret published by another process between our existence check and
    our publish must be returned instead of our own, and no temp file may
    remain."""
    path = tmp_path / ".secret"
    real_publish = secret_module._publish

    def racing_publish(tmp_path_, target):
        path.write_text("secret-from-other-process", encoding="utf-8")
        return real_publish(tmp_path_, target)

    monkeypatch.setattr(secret_module, "_publish", racing_publish)

    assert get_or_create_secret(str(path)) == "secret-from-other-process"
    assert path.read_text(encoding="utf-8") == "secret-from-other-process"
    assert _no_leftovers(tmp_path) == []


def test_empty_leftover_file_is_replaced(tmp_path):
    path = tmp_path / ".secret"
    path.write_text("", encoding="utf-8")

    value = get_or_create_secret(str(path))

    assert len(value) == SECRET_LENGTH
    assert path.read_text(encoding="utf-8") == value
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert _no_leftovers(tmp_path) == []


def test_interrupted_write_leaves_no_secret_behind(tmp_path, monkeypatch):
    """If the process dies while writing, the target must not exist (an empty
    file would otherwise be mistaken for a valid secret later)."""
    path = tmp_path / ".secret"

    def failing_fsync(fd):
        raise OSError("simulated crash during write")

    monkeypatch.setattr(secret_module.os, "fsync", failing_fsync)

    with pytest.raises(OSError):
        get_or_create_secret(str(path))

    assert not path.exists()
    assert _no_leftovers(tmp_path) == []


def _worker(path, queue):
    queue.put(get_or_create_secret(path))


def test_parallel_processes_agree_on_one_secret(tmp_path):
    path = str(tmp_path / ".secret")
    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()
    processes = [ctx.Process(target=_worker, args=(path, queue)) for _ in range(8)]
    for process in processes:
        process.start()
    results = [queue.get(timeout=60) for _ in processes]
    for process in processes:
        process.join(timeout=60)

    assert all(process.exitcode == 0 for process in processes)
    assert len(set(results)) == 1
    with open(path, encoding="utf-8") as f:
        assert f.read() == results[0]
    assert _no_leftovers(tmp_path) == []
