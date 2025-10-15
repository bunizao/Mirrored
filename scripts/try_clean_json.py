#!/usr/bin/env python3
"""Normalize loosely formatted JSON catalog responses."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def write_clean(obj: object, dest: Path) -> None:
    dest.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(',', ':')),
        encoding='utf-8',
    )


def extract_json(source_text: str) -> object:
    try:
        return json.loads(source_text)
    except Exception:
        pass

    match = re.search(r"```(?:json)?\s*({.*?})\s*```", source_text, re.S | re.I)
    if match:
        snippet = match.group(1)
        try:
            return json.loads(snippet)
        except Exception:
            pass

    stack: list[str] = []
    best_segment: str | None = None
    start_idx: int | None = None

    for idx, char in enumerate(source_text):
        if char == '{':
            if not stack:
                start_idx = idx
            stack.append(char)
        elif char == '}' and stack:
            stack.pop()
            if not stack and start_idx is not None:
                segment = source_text[start_idx:idx + 1]
                if best_segment is None or len(segment) > len(best_segment):
                    best_segment = segment
                start_idx = None

    if best_segment:
        try:
            return json.loads(best_segment.strip())
        except Exception:
            pass

    raise ValueError("Unable to locate valid JSON content")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: try_clean_json.py <input> <output>", file=sys.stderr)
        return 2

    src_path = Path(sys.argv[1])
    dst_path = Path(sys.argv[2])

    source_text = src_path.read_bytes().decode('utf-8', 'ignore')

    try:
        cleaned = extract_json(source_text)
    except ValueError:
        return 2

    write_clean(cleaned, dst_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

