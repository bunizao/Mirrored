#!/usr/bin/env python3
"""Download the Script-Hub plugin catalog via Cloudflare-aware HTTP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cloudscraper


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="https://hub.kelee.one/list.json",
        help="Plugin catalog URL to download.",
    )
    parser.add_argument(
        "--output",
        default="plugin_data.json",
        help="Path where the catalog should be written.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds.",
    )
    return parser.parse_args()


def download_catalog(url: str, timeout: int) -> str:
    scraper = cloudscraper.create_scraper(
        interpreter="nodejs",
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
        delay=10,
    )

    try:
        response = scraper.get(url, timeout=timeout)
    except Exception as exc:  # pragma: no cover - network diagnostics
        raise RuntimeError(f"Request to {url} failed: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(f"{url} returned HTTP {response.status_code}")

    text = response.text.strip()
    if not text:
        raise RuntimeError("Plugin list download produced an empty file")

    try:
        json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - validation
        raise RuntimeError("Downloaded plugin list is not valid JSON") from exc

    return text


def main() -> int:
    args = parse_args()
    try:
        catalog = download_catalog(args.url, args.timeout)
    except RuntimeError as exc:
        print(f"::error ::{exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.write_text(catalog, encoding="utf-8")
    print(f"✓ Downloaded plugin catalog from {args.url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
