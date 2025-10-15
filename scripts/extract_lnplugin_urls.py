#!/usr/bin/env python3
"""Extract LNPlugin download URLs from the plugin catalog JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Set


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="plugin_data.json",
        help="Path to the downloaded plugin catalog JSON file.",
    )
    parser.add_argument(
        "--output",
        default="lnplugin_urls.txt",
        help="Destination file for the extracted LNPlugin URLs.",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".lpx"],
        help="File extensions (including the leading dot) to collect.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print verbose information about URL discovery.",
    )
    return parser.parse_args()


def normalize_extensions(values: Iterable[str]) -> tuple[str, ...]:
    normalized = []
    for value in values:
        value = value.strip()
        if not value:
            continue
        if not value.startswith("."):
            value = f".{value}"
        normalized.append(value.lower())

    if not normalized:
        raise SystemExit("::error ::No file extensions provided for extraction")

    return tuple(dict.fromkeys(normalized))


def collect_urls(
    node: object,
    bucket: Set[str],
    extensions: tuple[str, ...],
    *,
    debug: bool,
    trail: str = "root",
) -> None:
    if isinstance(node, str):
        candidate = node.strip()
        if candidate.startswith("http"):
            if _matches_extension(candidate, extensions):
                bucket.add(candidate)
            elif debug:
                print(
                    f"[debug] skipped candidate at {trail}: {candidate}",
                    file=sys.stderr,
                )
        return

    if isinstance(node, dict):
        for key, value in node.items():
            child_trail = f"{trail}.{key}"
            collect_urls(value, bucket, extensions, debug=debug, trail=child_trail)
        return

    if isinstance(node, (list, tuple, set)):
        for index, value in enumerate(node):
            child_trail = f"{trail}[{index}]"
            collect_urls(value, bucket, extensions, debug=debug, trail=child_trail)
        return


def _matches_extension(candidate: str, extensions: tuple[str, ...]) -> bool:
    from urllib.parse import urlparse

    parsed = urlparse(candidate)
    path = parsed.path.lower()
    return path.endswith(extensions)


def extract_urls(
    source: Path, extensions: tuple[str, ...], *, debug: bool = False
) -> Iterable[str]:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit("::error ::Missing plugin_data.json")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"::error ::Failed to parse plugin catalog JSON: {exc}")

    urls: Set[str] = set()
    collect_urls(payload, urls, extensions, debug=debug)

    if not urls:
        raise SystemExit("::error ::No LNPlugin URLs discovered in plugin catalog")

    return sorted(urls)


def main() -> int:
    args = parse_args()
    source_path = Path(args.input)
    extensions = normalize_extensions(args.extensions)
    urls = list(extract_urls(source_path, extensions, debug=args.debug))

    output_path = Path(args.output)
    output_path.write_text("\n".join(urls) + "\n", encoding="utf-8")
    printable_exts = ", ".join(extensions)
    print(f"✓ Extracted {len(urls)} LNPlugin URLs matching: {printable_exts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
