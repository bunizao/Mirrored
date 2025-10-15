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
    parser.add_argument(
        "--host-prefix",
        action="append",
        default=[],
        type=parse_host_prefix,
        metavar="HOST=PREFIX",
        help=(
            "Prepend PREFIX to any discovered URL whose hostname matches HOST."
        ),
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


def parse_host_prefix(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "host-prefix values must be provided as HOST=PREFIX"
        )

    host, prefix = value.split("=", 1)
    host = host.strip().lower()
    prefix = prefix.strip()

    if not host or not prefix:
        raise argparse.ArgumentTypeError(
            "host-prefix entries require both a host and prefix"
        )

    return host, prefix


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
        if not candidate:
            return

        matches_found = False
        http_candidates = list(_iter_http_candidates(candidate))

        if not http_candidates and candidate.startswith("http"):
            http_candidates.append(candidate)

        for http_candidate in http_candidates:
            if _matches_extension(http_candidate, extensions):
                bucket.add(http_candidate)
                matches_found = True
            elif debug:
                print(
                    f"[debug] skipped candidate at {trail}: {http_candidate}",
                    file=sys.stderr,
                )

        if debug and not matches_found and not http_candidates:
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


def _iter_http_candidates(value: str) -> Iterable[str]:
    from urllib.parse import parse_qs, unquote, urlparse

    stack = [value]
    seen: Set[str] = set()

    while stack:
        current = stack.pop().strip()
        if not current or current in seen:
            continue
        seen.add(current)

        if current.startswith(("http://", "https://")):
            yield current
            continue

        if not current.startswith("loon://"):
            continue

        parsed = urlparse(current)

        if parsed.path:
            for part in parsed.path.split("/"):
                part = unquote(part)
                if part:
                    stack.append(part)

        if parsed.fragment:
            stack.append(unquote(parsed.fragment))

        if parsed.query:
            query = parse_qs(parsed.query, keep_blank_values=False)
            for values in query.values():
                for candidate in values:
                    stack.append(unquote(candidate))


def extract_urls(
    source: Path,
    extensions: tuple[str, ...],
    *,
    debug: bool = False,
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


def apply_host_prefixes(urls: Iterable[str], mapping: dict[str, str]) -> list[str]:
    if not mapping:
        return list(urls)

    from urllib.parse import urlparse

    normalized_map = {
        key.lower(): value for key, value in mapping.items() if value
    }

    def lookup(hostname: str) -> str | None:
        hostname = hostname.lower()
        if hostname in normalized_map:
            return normalized_map[hostname]

        for candidate, prefix in normalized_map.items():
            if candidate.startswith(".") and hostname.endswith(candidate):
                return prefix

        return None

    rewritten: list[str] = []
    for url in urls:
        parsed = urlparse(url)
        prefix = lookup(parsed.netloc)
        if prefix:
            trimmed = prefix.rstrip("/")
            rewritten.append(f"{trimmed}/{url}")
        else:
            rewritten.append(url)

    return rewritten


def main() -> int:
    args = parse_args()
    source_path = Path(args.input)
    extensions = normalize_extensions(args.extensions)
    urls = list(extract_urls(source_path, extensions, debug=args.debug))
    host_prefix_map = dict(args.host_prefix)
    urls = apply_host_prefixes(urls, host_prefix_map)

    output_path = Path(args.output)
    output_path.write_text("\n".join(urls) + "\n", encoding="utf-8")
    printable_exts = ", ".join(extensions)
    print(f"✓ Extracted {len(urls)} LNPlugin URLs matching: {printable_exts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
