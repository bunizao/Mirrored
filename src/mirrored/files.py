"""Filesystem helpers."""

from __future__ import annotations

from pathlib import Path


def write_if_changed(path: Path, data: bytes) -> bool:
    """Atomically write ``data`` to ``path``; return False if the file already matches.

    Writing through a temporary sibling means a crash never leaves a truncated
    file behind for users of the raw URL.
    """
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return True
