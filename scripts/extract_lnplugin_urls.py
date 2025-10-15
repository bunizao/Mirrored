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
    return parser.parse_args()


def collect_urls(node: object, bucket: Set[str]) -> None:
    if isinstance(node, str):
        candidate = node.strip()
        if candidate.startswith("http") and candidate.lower().endswith(".lpx"):
            bucket.add(candidate)
        return

    if isinstance(node, dict):
        for value in node.values():
            collect_urls(value, bucket)
        return

    if isinstance(node, (list, tuple, set)):
        for value in node:
            collect_urls(value, bucket)
        return


def extract_urls(source: Path) -> Iterable[str]:
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit("::error ::Missing plugin_data.json")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"::error ::Failed to parse plugin catalog JSON: {exc}")

    urls: Set[str] = set()
    collect_urls(payload, urls)

    if not urls:
        raise SystemExit("::error ::No LNPlugin URLs discovered in plugin catalog")

    return sorted(urls)


def main() -> int:
    args = parse_args()
    source_path = Path(args.input)
    urls = list(extract_urls(source_path))

    output_path = Path(args.output)
    output_path.write_text("\n".join(urls) + "\n", encoding="utf-8")
    print(f"✓ Extracted {len(urls)} LNPlugin URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
