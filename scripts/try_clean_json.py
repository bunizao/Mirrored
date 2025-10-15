#!/usr/bin/env python3
"""Normalize loosely formatted JSON content from LNPlugin sources."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def write_clean(obj: object, out_path: Path) -> None:
    """Write JSON with deterministic formatting."""
    out_path.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def clean_json(src_path: Path, out_path: Path) -> int:
    """Try to coerce text that should contain JSON into normalized JSON."""
    src = src_path.read_bytes().decode("utf-8", "ignore")

    def dump(obj: object) -> int:
        write_clean(obj, out_path)
        return 0

    try:
        return dump(json.loads(src))
    except Exception:  # noqa: BLE001 - best-effort parsing
        pass

    fenced = re.search(r"```(?:json)?\\s*({.*?})\\s*```", src, re.S | re.I)
    if fenced:
        try:
            return dump(json.loads(fenced.group(1)))
        except Exception:  # noqa: BLE001 - best-effort parsing
            pass

    stack: list[int] = []
    best: str | None = None
    start: int | None = None
    for i, ch in enumerate(src):
        if ch == "{":
            if not stack:
                start = i
            stack.append(i)
        elif ch == "}" and stack:
            stack.pop()
            if not stack and start is not None:
                segment = src[start : i + 1]
                if best is None or len(segment) > len(best):
                    best = segment
                start = None

    if best:
        try:
            return dump(json.loads(best.strip()))
        except Exception:  # noqa: BLE001 - best-effort parsing
            pass

    return 2


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: try_clean_json.py <src_path> <out_path>", file=sys.stderr)
        return 2

    src_path = Path(argv[1])
    out_path = Path(argv[2])
    return clean_json(src_path, out_path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
