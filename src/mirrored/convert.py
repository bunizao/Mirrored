"""Convert Loon plugins into Surge modules through a local Script-Hub instance.

A failed conversion never touches the existing module: users keep the last
known-good copy instead of losing it to an upstream outage.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse

import requests

from mirrored import gha
from mirrored.config import ConvertConfig
from mirrored.files import write_if_changed


@dataclass
class ConvertResult:
    name: str
    source_url: str
    status: str  # "updated", "unchanged" or "failed"
    detail: str = ""


def plugin_name(url: str) -> str:
    """Derive the module name from a plugin URL, e.g. ``.../Foo.lpx?x=1`` -> ``Foo``."""
    base = urlparse(url).path.rsplit("/", 1)[-1].strip()
    name = base
    for suffix in (".lpx", ".plugin"):
        name = name.removesuffix(suffix)
    return name.strip() or base


def _uri(value: str) -> str:
    # Same escaping as jq's @uri: everything except RFC 3986 unreserved characters.
    return quote(value, safe="")


def needs_proxy(url: str, proxy_hosts: Sequence[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith(f".{h}") for h in proxy_hosts)


def scripthub_url(source_url: str, name: str, config: ConvertConfig, proxy_base: str = "") -> str:
    prefix = proxy_base if proxy_base and needs_proxy(source_url, config.proxy_hosts) else ""
    base = config.scripthub_url.rstrip("/")
    query = "&".join(
        [
            "type=loon-plugin",
            "target=surge-module",
            f"category={_uri(config.category)}",
            f"headers={_uri(f'User-Agent: {config.user_agent}')}",
        ]
    )
    # Script-Hub expects the raw source URL between the _start_/_end_ markers.
    return f"{base}/file/_start_/{prefix}{source_url}/_end_/{_uri(name)}.sgmodule?{query}"


def looks_like_module(text: str) -> bool:
    """Script-Hub output always starts with a ``#!name=`` header."""
    return "#!name=" in text[:4096]


def wait_for_scripthub(session: requests.Session, url: str, *, timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            session.get(url, timeout=5)
            return
        except requests.RequestException:
            if time.monotonic() > deadline:
                raise
            time.sleep(3)


def convert_one(
    session: requests.Session,
    source_url: str,
    name: str,
    output: Path,
    config: ConvertConfig,
    proxy_base: str,
) -> ConvertResult:
    url = scripthub_url(source_url, name, config, proxy_base)
    try:
        response = session.get(url, timeout=(30, 120))
    except requests.RequestException as exc:
        return ConvertResult(name, source_url, "failed", type(exc).__name__)
    if response.status_code != 200:
        return ConvertResult(name, source_url, "failed", f"HTTP {response.status_code}")
    text = response.content.decode("utf-8", "replace")
    if not looks_like_module(text):
        return ConvertResult(name, source_url, "failed", "response is not a module")
    changed = write_if_changed(output, response.content)
    return ConvertResult(name, source_url, "updated" if changed else "unchanged")


def convert_all(
    session: requests.Session,
    plugin_urls: Sequence[str],
    *,
    root: Path,
    config: ConvertConfig,
    proxy_base: str = "",
    workers: int = 4,
) -> list[ConvertResult]:
    # Several URLs can share a file name; the last one in sorted order wins,
    # matching the historical behaviour, but the clash is reported.
    by_name: dict[str, str] = {}
    for url in sorted(plugin_urls):
        name = plugin_name(url)
        if name in by_name:
            gha.warning(
                f"{name}.sgmodule is claimed by {by_name[name]} and {url}; using the latter"
            )
        by_name[name] = url

    output_dir = root / config.output_dir
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                convert_one,
                session,
                url,
                name,
                output_dir / f"{name}.sgmodule",
                config,
                proxy_base,
            )
            for name, url in sorted(by_name.items())
        ]
        return [f.result() for f in futures]


def report(results: Sequence[ConvertResult]) -> None:
    failed = [r for r in results if r.status == "failed"]
    updated = [r for r in results if r.status == "updated"]
    lines = [
        "## Plugin conversion",
        "",
        f"{len(results)} plugins · {len(updated)} updated · "
        f"{len(results) - len(updated) - len(failed)} unchanged · {len(failed)} failed "
        "(existing modules kept)",
    ]
    if updated:
        lines += ["", "**Updated:** " + ", ".join(r.name for r in updated)]
    if failed:
        rows = [(r.name, r.detail, r.source_url) for r in failed]
        lines += [
            "",
            "<details><summary>Failed conversions</summary>",
            "",
            gha.table(["Module", "Reason", "Source"], rows),
            "",
            "</details>",
        ]
        gha.warning(
            f"{len(failed)} of {len(results)} plugin conversions failed; "
            "the previous modules were kept. See the job summary."
        )
    gha.summary("\n".join(lines))
