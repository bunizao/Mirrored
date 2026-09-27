"""Download the Loon plugin catalog and extract plugin URLs from it."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Sequence
from urllib.parse import parse_qs, unquote, urlparse

from mirrored import gha


class CatalogError(Exception):
    """The plugin catalog could not be downloaded or contained no plugins."""


def download_catalog(urls: Sequence[str], *, timeout: int = 60) -> object:
    """Fetch the first catalog URL that returns valid JSON.

    The catalog sits behind Cloudflare, so a Cloudflare-aware client is required.
    """
    import cloudscraper  # Imported lazily: heavy and only needed here.

    scraper = cloudscraper.create_scraper(
        interpreter="nodejs",
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
        delay=10,
    )
    failures = []
    for url in urls:
        try:
            response = scraper.get(url, timeout=timeout)
            if response.status_code != 200:
                raise CatalogError(f"HTTP {response.status_code}")
            return json.loads(response.text)
        except Exception as exc:  # noqa: BLE001 - any failure moves on to the next mirror
            failures.append(f"{url}: {exc}")
            gha.warning(f"Plugin catalog unavailable at {url}: {exc}")
    raise CatalogError("; ".join(failures) or "no catalog URLs configured")


def extract_plugin_urls(payload: object, extensions: Iterable[str]) -> list[str]:
    """Return every http(s) URL in ``payload`` whose path ends with one of ``extensions``.

    The catalog nests URLs arbitrarily and sometimes wraps them in ``loon://``
    install links, so the whole JSON tree is walked.
    """
    suffixes = tuple(_normalize_extension(ext) for ext in extensions)
    found: set[str] = set()
    for value in _iter_strings(payload):
        for candidate in _iter_http_candidates(value.strip()):
            if urlparse(candidate).path.lower().endswith(suffixes):
                found.add(candidate)
    return sorted(found)


def _normalize_extension(ext: str) -> str:
    ext = ext.strip().lower()
    return ext if ext.startswith(".") else f".{ext}"


def _iter_strings(node: object) -> Iterator[str]:
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _iter_strings(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _iter_strings(value)


def _iter_http_candidates(value: str) -> Iterator[str]:
    """Yield http(s) URLs in ``value``, unwrapping ``loon://`` links recursively."""
    stack = [value]
    seen: set[str] = set()
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
        stack.extend(unquote(part) for part in parsed.path.split("/") if part)
        if parsed.fragment:
            stack.append(unquote(parsed.fragment))
        for values in parse_qs(parsed.query).values():
            stack.extend(unquote(v) for v in values)
