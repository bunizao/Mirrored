"""Mirror the external JavaScript files that modules load and rewrite their links."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import requests

from mirrored import gha
from mirrored.config import ScriptsConfig
from mirrored.fetch import FetchError, fetch
from mirrored.files import write_if_changed

# `script-path=<url>` where the URL contains `.js`; stops at whitespace, commas and quotes.
SCRIPT_PATH_RE = re.compile(r'script-path\s*=\s*(https?://[^\s,"]+\.js[^\s,"]*)')

# Anything shorter is an error page or placeholder, not a script.
MIN_SCRIPT_BYTES = 11


@dataclass
class ScriptResult:
    url: str
    filename: str
    status: str  # "updated", "unchanged", "failed" or "skipped"
    detail: str = ""


def script_filename(url: str) -> str:
    """``https://h/a/b.js?x`` -> ``b.js``; a ``.js`` suffix is appended when missing."""
    path = re.split(r"[?#]", url, maxsplit=1)[0]
    name = path.rstrip("/").rsplit("/", 1)[-1]
    return name if name.endswith(".js") else f"{name}.js"


def find_script_urls(texts: Iterable[str], skip_patterns: Sequence[str]) -> list[str]:
    urls = {m.group(1) for text in texts for m in SCRIPT_PATH_RE.finditer(text)}
    return sorted(u for u in urls if not any(p in u for p in skip_patterns))


def module_files(directory: Path, exclude: Sequence[str]) -> list[Path]:
    return sorted(p for p in directory.rglob("*.sgmodule") if p.name not in exclude)


def mirror_scripts(
    session: requests.Session,
    *,
    root: Path,
    modules_dir: Path,
    config: ScriptsConfig,
    proxy_base: str = "",
    proxy_hosts: Sequence[str] = (),
) -> list[ScriptResult]:
    modules = module_files(modules_dir, config.exclude)
    texts = {path: path.read_text(encoding="utf-8", errors="surrogateescape") for path in modules}
    urls = find_script_urls(texts.values(), config.skip_patterns)
    output_dir = root / config.output_dir

    results: list[ScriptResult] = []
    rewrites: dict[str, str] = {}
    claimed: dict[str, str] = {}
    for url in urls:
        filename = script_filename(url)
        # Two different scripts with the same file name would overwrite each other
        # and silently point one module at the wrong code, so only the first is mirrored.
        if claimed.setdefault(filename, url) != url:
            results.append(
                ScriptResult(url, filename, "skipped", f"name clash with {claimed[filename]}")
            )
            continue
        try:
            fetched = fetch(
                session,
                url,
                proxy_base=proxy_base,
                proxy_hosts=proxy_hosts,
                validate=lambda content: len(content) >= MIN_SCRIPT_BYTES,
            )
        except FetchError as exc:
            results.append(ScriptResult(url, filename, "failed", str(exc)))
            continue
        changed = write_if_changed(output_dir / filename, fetched.content)
        results.append(ScriptResult(url, filename, "updated" if changed else "unchanged"))
        rewrites[url] = f"{config.mirror_base}/{filename}"

    for path, text in texts.items():
        new_text = text
        for original, mirrored in rewrites.items():
            new_text = new_text.replace(original, mirrored)
        if new_text != text:
            write_if_changed(path, new_text.encode("utf-8", "surrogateescape"))
    return results


def report(results: Sequence[ScriptResult]) -> None:
    counts = {s: sum(r.status == s for r in results) for s in ("updated", "unchanged")}
    problems = [r for r in results if r.status in ("failed", "skipped")]
    lines = [
        "## Script mirroring",
        "",
        f"{len(results)} external scripts · {counts['updated']} updated · "
        f"{counts['unchanged']} unchanged · {len(problems)} not mirrored",
    ]
    if problems:
        rows = [(r.filename, r.status, r.detail, r.url) for r in problems]
        lines += [
            "",
            "<details><summary>Scripts left on their original URL</summary>",
            "",
            gha.table(["File", "Status", "Reason", "URL"], rows),
            "",
            "</details>",
        ]
    gha.summary("\n".join(lines))
