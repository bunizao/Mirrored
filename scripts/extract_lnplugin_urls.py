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


def collect_urls(node: object, bucket: Set[str], extensions: tuple[str, ...]) -> None:
    if isinstance(node, str):
        candidate = node.strip()
        if candidate.startswith("http") and candidate.lower().endswith(extensions):
            bucket.add(candidate)
        return

    if isinstance(node, dict):
        for value in node.values():
            collect_urls(value, bucket, extensions)
        return

    if isinstance(node, (list, tuple, set)):
        for value in node:
            collect_urls(value, bucket, extensions)
        return


def extract_urls(source: Path, extensions: tuple[str, ...]) -> Iterable[str]:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit("::error ::Missing plugin_data.json")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"::error ::Failed to parse plugin catalog JSON: {exc}")

    urls: Set[str] = set()
    collect_urls(payload, urls, extensions)

    if not urls:
        raise SystemExit("::error ::No LNPlugin URLs discovered in plugin catalog")

    return sorted(urls)


def main() -> int:
    args = parse_args()
    source_path = Path(args.input)
    extensions = normalize_extensions(args.extensions)
    urls = list(extract_urls(source_path, extensions))

    output_path = Path(args.output)
    output_path.write_text("\n".join(urls) + "\n", encoding="utf-8")
    printable_exts = ", ".join(extensions)
    print(f"✓ Extracted {len(urls)} LNPlugin URLs matching: {printable_exts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
