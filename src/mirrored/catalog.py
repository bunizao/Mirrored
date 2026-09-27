"""Download the Loon plugin catalog and extract plugin URLs from it."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from mirrored import gha
from mirrored.files import write_if_changed
from mirrored.http import make_browser_session


class CatalogError(Exception):
    """The plugin catalog could not be downloaded or contained no plugins."""


def download_catalog(urls: Sequence[str], *, timeout: int = 60) -> object:
    """Fetch the first catalog URL that returns valid JSON.

    The catalog sits behind Cloudflare, so a browser-like client is required.
    """
    scraper = make_browser_session()
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


def plugin_filename(url: str) -> str:
    return urlparse(url).path.rsplit("/", 1)[-1].strip()


def plugin_name(url: str) -> str:
    """Derive the module name from a plugin URL, e.g. ``.../Foo.lpx?x=1`` -> ``Foo``."""
    name = plugin_filename(url)
    for suffix in (".lpx", ".plugin"):
        name = name.removesuffix(suffix)
    return name.strip() or plugin_filename(url)


def plugin_records(payload: object, extensions: Iterable[str]) -> dict:
    """Trim the catalog to the metadata the index page shows, keyed to module files."""
    if not isinstance(payload, dict):
        return {"name": "", "notice": [], "plugins": []}
    suffixes = tuple(_normalize_extension(ext) for ext in extensions)
    plugins = []
    for entry in payload.get("lists") or []:
        if not isinstance(entry, dict):
            continue
        urls = [
            u
            for u in _iter_http_candidates(str(entry.get("url", "")))
            if urlparse(u).path.lower().endswith(suffixes)
        ]
        if not urls:
            continue
        plugins.append(
            {
                "file": f"{plugin_name(urls[0])}.sgmodule",
                "name": str(entry.get("name", "")),
                "desc": str(entry.get("desc", "")),
                "tags": [str(t) for t in entry.get("tag") or []],
                "icon": str(entry.get("icon", "")),
                "date": str(entry.get("date", "")),
                "authors": [
                    {"name": str(a.get("name", "")), "homepage": str(a.get("homepage", ""))}
                    for a in entry.get("author") or []
                    if isinstance(a, dict)
                ],
                "source": urls[0],
            }
        )
    notice = payload.get("notice") or []
    return {
        "name": str(payload.get("name", "")),
        "notice": [str(n) for n in notice] if isinstance(notice, list) else [str(notice)],
        "plugins": plugins,
    }


def save_records(path: Path, records: dict) -> bool:
    data = json.dumps(records, ensure_ascii=False, indent=1) + "\n"
    return write_if_changed(path, data.encode("utf-8"))
