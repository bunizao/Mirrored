"""Convert Loon plugins into Surge modules through a local Script-Hub instance.

Plugins are downloaded here (see ``mirrored.fetch``) and handed to Script-Hub
from a short-lived local HTTP server, so Script-Hub never needs to reach the
upstream itself. A plugin that cannot be fetched or converted never touches
the existing module: users keep the last known-good copy.
"""

from __future__ import annotations

import tempfile
import threading
import time
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

import requests

from mirrored import gha
from mirrored.catalog import plugin_filename, plugin_name
from mirrored.config import ConvertConfig
from mirrored.credit import add_credit_bytes
from mirrored.fetch import FetchError, fetch
from mirrored.files import write_if_changed


@dataclass
class ConvertResult:
    name: str
    source_url: str
    status: str  # "converted" or "failed"
    detail: str = ""
    via: str = ""  # How the plugin was fetched: "direct" or "proxy".


def _uri(value: str) -> str:
    # Same escaping as jq's @uri: everything except RFC 3986 unreserved characters.
    return quote(value, safe="")


def scripthub_url(source_url: str, name: str, config: ConvertConfig) -> str:
    base = config.scripthub_url.rstrip("/")
    query = "&".join(
        [
            "type=loon-plugin",
            "target=surge-module",
            f"headers={_uri(f'User-Agent: {config.user_agent}')}",
        ]
    )
    # Script-Hub expects the raw source URL between the _start_/_end_ markers.
    return f"{base}/file/_start_/{source_url}/_end_/{_uri(name)}.sgmodule?{query}"


def looks_like_module(content: bytes) -> bool:
    """Both Loon plugins and Script-Hub output start with a ``#!name=`` header."""
    return b"#!name=" in content[:4096]


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


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@contextmanager
def serve_directory(directory: Path, host: str) -> Iterator[str]:
    """Serve ``directory`` over HTTP on an ephemeral port; yields the base URL."""
    handler = partial(_QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer((host, 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _dedupe(plugin_urls: Sequence[str]) -> dict[str, str]:
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
    return by_name


def convert_all(
    fetch_session: requests.Session,
    scripthub: requests.Session,
    plugin_urls: Sequence[str],
    *,
    root: Path,
    config: ConvertConfig,
    proxy_base: str = "",
    proxy_session: requests.Session | None = None,
    workers: int = 4,
) -> list[ConvertResult]:
    by_name = _dedupe(plugin_urls)
    output_dir = root / config.output_dir
    results: dict[str, ConvertResult] = {}

    with tempfile.TemporaryDirectory(prefix="plugins-") as tmp, ThreadPoolExecutor(workers) as pool:
        staging = Path(tmp)

        # 1. Download every plugin through the fallback chain.
        def download(name: str, url: str) -> tuple[str, str]:
            fetched = fetch(
                fetch_session,
                url,
                proxy_base=proxy_base,
                proxy_hosts=config.proxy_hosts,
                user_agents=config.fetch_user_agents,
                proxy_session=proxy_session,
                validate=looks_like_module,
            )
            (staging / plugin_filename(url)).write_bytes(fetched.content)
            return name, fetched.via

        futures = {pool.submit(download, n, u): n for n, u in by_name.items()}
        fetched_via: dict[str, str] = {}
        for future, name in futures.items():
            try:
                fetched_via[name] = future.result()[1]
            except FetchError as exc:
                results[name] = ConvertResult(name, by_name[name], "failed", f"fetch: {exc}")

        # 2. Let Script-Hub convert the local copies.
        with serve_directory(staging, config.serve_host) as base:

            def convert(name: str) -> ConvertResult:
                url = by_name[name]
                local = f"{base}/{quote(plugin_filename(url))}"
                result = ConvertResult(name, url, "failed", via=fetched_via[name])
                try:
                    response = scripthub.get(scripthub_url(local, name, config), timeout=(30, 120))
                except requests.RequestException as exc:
                    result.detail = f"convert: {type(exc).__name__}"
                    return result
                if response.status_code != 200:
                    result.detail = f"convert: HTTP {response.status_code}"
                elif not looks_like_module(response.content):
                    result.detail = "convert: response is not a module"
                else:
                    module = add_credit_bytes(response.content, url)
                    write_if_changed(output_dir / f"{name}.sgmodule", module)
                    result.status = "converted"
                return result

            for result in pool.map(convert, sorted(fetched_via)):
                results[result.name] = result

    return [results[name] for name in sorted(results)]


def report(results: Sequence[ConvertResult]) -> None:
    failed = [r for r in results if r.status == "failed"]
    proxied = sum(r.via == "proxy" for r in results)
    lines = [
        "## Plugin conversion",
        "",
        f"{len(results)} plugins · {len(results) - len(failed)} converted · "
        f"{len(failed)} failed (existing modules kept) · {proxied} fetched via proxy",
    ]
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
