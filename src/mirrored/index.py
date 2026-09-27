"""Render the Chinese index pages (README.md per output directory, plus a root page).

The pages are generated from each file's own metadata header and contain no
timestamps, so they only change when the listed files change.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from mirrored.config import IndexConfig, IndexPage
from mirrored.files import write_if_changed

GENERATED_NOTE = "> 本页由 `mirrored build-index` 自动生成，请勿手动编辑。"
DESC_LIMIT = 90

# `#!name=...` / `#!name = ...` headers (Surge, Loon, Quantumult X).
_HASH_META = re.compile(r"^#!\s*(name|desc)\s*=\s*(.*)$", re.MULTILINE)
# `name: ...` / `desc: ...` top-level YAML keys (Stash overrides).
_YAML_META = re.compile(r"^(name|desc):[ \t]*(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class Entry:
    filename: str
    name: str
    desc: str


def read_metadata(text: str) -> dict[str, str]:
    """Return the first ``name`` and ``desc`` found in a module header."""
    head = text[:8192]
    meta: dict[str, str] = {}
    for key, value in _HASH_META.findall(head):
        meta.setdefault(key, value)
    for match in _YAML_META.finditer(head):
        key, value = match.group(1), match.group(2).strip()
        if value in ("|", "|-", ">", ">-"):
            # Block scalar: the value is on the following indented line.
            rest = head[match.end() :].lstrip("\n")
            value = rest.splitlines()[0] if rest else ""
        meta.setdefault(key, value.strip().strip("\"'"))
    return meta


def clean(text: str, limit: int | None = None) -> str:
    text = text.replace("\\n", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip().strip("\"'").strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def cell(text: str) -> str:
    """Escape text for a Markdown table cell."""
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def collect(directory: Path, ext: str) -> list[Entry]:
    entries = []
    for path in sorted(directory.glob(f"*.{ext}"), key=lambda p: p.name.lower()):
        meta = read_metadata(path.read_text(encoding="utf-8", errors="replace"))
        entries.append(
            Entry(
                filename=path.name,
                name=clean(meta.get("name", "")) or path.stem,
                desc=clean(meta.get("desc", ""), DESC_LIMIT),
            )
        )
    return entries


def _table(entries: Iterable[Entry], raw_base: str, rel_dir: str) -> list[str]:
    lines = ["| 名称 | 说明 | 链接 |", "| --- | --- | --- |"]
    for e in entries:
        url = f"{raw_base}/{rel_dir}/{e.filename}"
        lines.append(f"| {cell(e.name)} | {cell(e.desc) or '—'} | [{cell(e.filename)}]({url}) |")
    return lines


def render_page(root: Path, page: IndexPage, config: IndexConfig) -> str:
    lines = [f"# {page.title}", "", GENERATED_NOTE, ""]
    if page.intro:
        lines += [page.intro, ""]
    if page.upstream:
        lines += [f"上游项目：<{page.upstream}>", ""]
    lines += [
        "**使用方法**：在对应 App 中选择「从 URL 安装 / 添加」，粘贴下表中文件的链接即可"
        "（右键链接复制，或点开后复制浏览器地址）。",
        "",
    ]

    for section in page.sections:
        entries = collect(root / section.dir, section.ext)
        pinned = [e for e in entries if e.filename in page.pinned]
        rest = [e for e in entries if e.filename not in page.pinned]
        lines += [f"## {section.label}（{len(entries)} 个）", ""]
        if pinned:
            lines += ["**推荐**", "", *_table(pinned, config.raw_base, section.dir), ""]
        if rest:
            lines += [*_table(rest, config.raw_base, section.dir), ""]
        if not entries:
            lines += ["暂无文件。", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_root(config: IndexConfig) -> str:
    lines = [
        "# Mirrored 中文索引",
        "",
        GENERATED_NOTE,
        "",
        "自动同步多个开源项目的模块与脚本，统一托管在同一个 raw 地址下，"
        "可直接用于 Surge / Loon / Stash / Egern / Quantumult X / Shadowrocket。",
        "",
        "## 快速开始",
        "",
        "去广告合集（推荐），在 App 中「从 URL 安装模块」：",
        "",
        "```text",
        f"{config.raw_base}/Chores/sgmodule/All-in-One-2.x.sgmodule",
        "```",
        "",
        "## 目录索引",
        "",
        "| 目录 | 内容 | 上游 |",
        "| --- | --- | --- |",
    ]
    for page in config.pages:
        upstream = f"<{page.upstream}>" if page.upstream else "—"
        lines.append(f"| [{page.title}]({page.path}/README.md) | {cell(page.intro)} | {upstream} |")
    lines += [
        "",
        "## 其他文件",
        "",
        "- 去广告规则集："
        f"[`Chores/ruleset/reject.list`]({config.raw_base}/Chores/ruleset/reject.list)",
        "- 模块引用的外部脚本镜像：[`Chores/js/`](Chores/js)",
        "",
        "## 声明",
        "",
        "仅供学习与个人备份使用，所有模块与脚本的版权归原作者所有。"
        "如有侵权请提交 issue，将及时删除。",
    ]
    return "\n".join(lines) + "\n"


def build(root: Path, config: IndexConfig, pages: Iterable[str] | None = None) -> list[str]:
    """Write the root page and the selected directory pages; return the changed paths."""
    selected = set(pages) if pages else None
    changed = []
    if write_if_changed(root / config.root, render_root(config).encode("utf-8")):
        changed.append(config.root)
    for page in config.pages:
        if selected is not None and page.path not in selected:
            continue
        target = f"{page.path}/README.md"
        if write_if_changed(root / target, render_page(root, page, config).encode("utf-8")):
            changed.append(target)
    return changed
