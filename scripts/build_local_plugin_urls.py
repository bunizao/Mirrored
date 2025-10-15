#!/usr/bin/env python3
"""Generate local HTTP URLs for mirrored LNPlugin artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import quote


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="lnplugin_files.txt",
        help="File containing newline-delimited LNPlugin paths.",
    )
    parser.add_argument(
        "--output",
        default="plugin_urls.txt",
        help="Destination file for the generated URLs.",
    )
    parser.add_argument(
        "--base-url",
        default="http://host.docker.internal:8000",
        help="Base URL used to serve the mirrored artifacts.",
    )
    return parser.parse_args()


def read_paths(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"::error ::Missing input file: {path}")

    entries = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    filtered = [entry for entry in entries if entry]

    if not filtered:
        raise SystemExit("::error ::lnplugin_files.txt is empty")

    return filtered


def build_urls(paths: list[str], base_url: str) -> list[str]:
    urls: list[str] = []
    for item in paths:
        name = Path(item).name
        encoded = quote(name)
        urls.append(f"{base_url}/{encoded}")
    return urls


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    files = read_paths(input_path)
    urls = build_urls(files, args.base_url.rstrip("/"))

    output_path.write_text("\n".join(urls) + "\n", encoding="utf-8")
    print(f"✓ Generated {len(urls)} plugin URLs from {input_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
