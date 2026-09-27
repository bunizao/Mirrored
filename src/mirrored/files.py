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


def snapshot(directory: Path, pattern: str = "*") -> dict[Path, bytes]:
    """Map every file under ``directory`` matching ``pattern`` to its contents."""
    if not directory.is_dir():
        return {}
    return {p: p.read_bytes() for p in directory.rglob(pattern) if p.is_file()}


def changed_files(before: dict[Path, bytes], after: dict[Path, bytes]) -> list[Path]:
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
