"""Mirror assets from the latest GitHub release of upstream repositories."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests

from mirrored import gha
from mirrored.config import ReleaseSource
from mirrored.files import write_if_changed

API_ROOT = "https://api.github.com"


class UpstreamError(Exception):
    """An upstream repository or file could not be fetched."""


@dataclass
class RepoResult:
    source: str
    repo: str
    updated: list[str] = field(default_factory=list)
    unchanged: int = 0
    error: str | None = None
    # Paths (relative to the repository root) that upstream currently publishes.
    published: list[str] = field(default_factory=list)
    extra: bool = False


def extension_of(name: str) -> str:
    # Mirrors the shell expansion "${name##*.}": no dot means the whole name.
    return name.rsplit(".", 1)[-1]


def apply_argument_overrides(text: str, overrides: Mapping[str, str]) -> str:
    """Force default values into the ``#!arguments=`` header line.

    Only the first ``Key:value`` pair per key is replaced, and only on lines that
    start exactly with ``#!arguments=`` (``#!arguments-desc=`` is left alone).
    """
    if not overrides:
        return text
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if not line.startswith("#!arguments="):
            continue
        for key, value in overrides.items():
            pattern = re.compile(rf"({re.escape(key)}:)[^,]*")
            line = pattern.sub(lambda m, v=value: m.group(1) + v, line, count=1)
        lines[index] = line
    return "\n".join(lines)


def _api_error(response: requests.Response) -> str:
    try:
        message = response.json().get("message")
    except ValueError:
        message = None
    return f"HTTP {response.status_code}" + (f": {message}" if message else "")


def fetch_latest_release(session: requests.Session, repo: str) -> dict:
    """Return the latest release, following renames and transfers of the repository."""
    response = session.get(f"{API_ROOT}/repos/{repo}/releases/latest", timeout=30)
    # requests follows the 301 GitHub sends for renamed/transferred repositories.
    if not response.ok:
        raise UpstreamError(_api_error(response))
    release = response.json()
    if not isinstance(release, dict):
        raise UpstreamError("unexpected response payload")

    if response.history:
        moved_to = _repo_from_html_url(release.get("html_url", ""))
        hint = f" to {moved_to}" if moved_to else ""
        gha.notice(f"{repo} has moved{hint}; update config/releases.yaml.")
    return release


def _repo_from_html_url(url: str) -> str | None:
    parts = urlparse(url).path.strip("/").split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else None


def download(session: requests.Session, url: str) -> bytes:
    response = session.get(url, timeout=60)
    if response.status_code != 200:
        raise UpstreamError(f"{url}: HTTP {response.status_code}")
    if not response.content:
        raise UpstreamError(f"{url}: empty response")
    return response.content


def _store(path: Path, data: bytes, overrides: Mapping[str, Mapping[str, str]]) -> bool:
    ext_overrides = overrides.get(extension_of(path.name))
    if ext_overrides:
        # surrogateescape round-trips any bytes that are not valid UTF-8 untouched.
        text = data.decode("utf-8", "surrogateescape")
        data = apply_argument_overrides(text, ext_overrides).encode("utf-8", "surrogateescape")
    return write_if_changed(path, data)


def sync_source(
    source: ReleaseSource,
    *,
    root: Path,
    api: requests.Session,
    downloads: requests.Session,
) -> list[RepoResult]:
    results = []
    for repo in source.repos:
        result = RepoResult(source.name, repo)
        results.append(result)
        try:
            release = fetch_latest_release(api, repo)
            for asset in release.get("assets") or []:
                name = asset.get("name", "")
                route = source.routes.get(extension_of(name))
                if not route:
                    continue
                result.published.append(f"{route}/{name}")
                data = download(downloads, asset["browser_download_url"])
                if _store(root / route / name, data, source.argument_overrides):
                    result.updated.append(f"{route}/{name}")
                else:
                    result.unchanged += 1
        except (UpstreamError, requests.RequestException) as exc:
            result.error = str(exc)
            gha.warning(f"{repo}: {exc}")

    for extra in source.extra_files:
        result = RepoResult(source.name, extra.url, published=[extra.path], extra=True)
        results.append(result)
        try:
            data = download(downloads, extra.url)
            if _store(root / extra.path, data, source.argument_overrides):
                result.updated.append(extra.path)
            else:
                result.unchanged += 1
        except (UpstreamError, requests.RequestException) as exc:
            result.error = str(exc)
            gha.warning(f"{extra.url}: {exc}")
    return results


def find_stale(source: ReleaseSource, results: list[RepoResult], root: Path) -> list[str] | None:
    """Files in the source's directories that upstream no longer publishes.

    Returns None when any repository failed to sync: its assets are unknown, so
    nothing may be judged stale (a failed fetch must never delete files).
    """
    if any(r.error for r in results if not r.extra):
        return None
    published = {p for r in results for p in r.published}
    present = {
        path.relative_to(root).as_posix()
        for ext, route in source.routes.items()
        for path in (root / route).glob(f"*.{ext}")
        if path.is_file()
    }
    return sorted(present - published)


def report(results: list[RepoResult]) -> None:
    rows = [
        (
            r.source,
            r.repo,
            "❌ " + r.error if r.error else "✅",
            ", ".join(r.updated) or "—",
            r.unchanged,
        )
        for r in results
    ]
    gha.summary(
        "## Upstream release sync\n\n"
        + gha.table(["Source", "Repository", "Status", "Updated", "Unchanged"], rows)
    )
