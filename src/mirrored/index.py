"""Render the Chinese index page (README.zh-CN.md).

The page combines the plugin catalog metadata saved by ``build-modules`` with
the metadata headers of the mirrored files. It contains no timestamps of its
own, so it only changes when the listed files or the catalog change.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from mirrored.config import IndexConfig, IndexProject
from mirrored.files import write_if_changed

GENERATED_NOTE = "> 本页随上游自动更新。"
DESC_LIMIT = 48
# Groups this small are expanded by default.
OPEN_GROUP_LIMIT = 10
# Tags with fewer plugins than this are folded into a shared group.
MIN_GROUP_SIZE = 3
OTHER_GROUP = "其他"

FORMAT_LABELS = {
    "sgmodule": "Surge / Egern",
    "plugin": "Loon",
    "stoverride": "Stash",
    "snippet": "Quantumult X",
}
INSTALL_HINTS = {
    "sgmodule": "模块 → 安装新模块，粘贴 `.sgmodule` 链接",
    "plugin": "配置 → 插件 → 添加，粘贴 `.plugin` 链接",
    "stoverride": "覆写 → 从 URL 安装，粘贴 `.stoverride` 链接",
    "snippet": "重写 → 引用，粘贴 `.snippet` 链接",
}

# `#!name=...` / `#!name = ...` headers (Surge, Loon, Quantumult X).
_HASH_META = re.compile(r"^#!\s*(name|desc)\s*=\s*(.*)$", re.MULTILINE)
# `name: ...` / `desc: ...` top-level YAML keys (Stash overrides).
_YAML_META = re.compile(r"^(name|desc):[ \t]*(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class Entry:
    filename: str
    name: str
    desc: str


# --- text helpers ----------------------------------------------------------


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
    # Private-use glyphs (e.g. the Apple logo) render as boxes outside Apple devices.
    text = re.sub("[\ue000-\uf8ff]", "", text)
    text = re.sub(r"\s+", " ", text).strip().strip("\"'").strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def cell(text: str) -> str:
    """Escape text for a Markdown table cell."""
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def read_entry(path: Path) -> Entry:
    meta = read_metadata(path.read_text(encoding="utf-8", errors="replace"))
    return Entry(
        filename=path.name,
        name=clean(meta.get("name", "")) or path.stem,
        desc=clean(meta.get("desc", ""), DESC_LIMIT),
    )


def _duplicates(names: list[str]) -> set[str]:
    seen: set[str] = set()
    return {name for name in names if name in seen or seen.add(name)}


def _disambiguate(label: str, name: str, stem: str, duplicates: set[str]) -> str:
    """Append the file stem to labels whose display name is not unique."""
    return f"{label} <sub>{cell(stem)}</sub>" if name in duplicates else label


def _details(summary: str, body: list[str], *, open_: bool) -> list[str]:
    tag = "<details open>" if open_ else "<details>"
    return [tag, f"<summary>{summary}</summary>", "", *body, "", "</details>", ""]


# --- sections --------------------------------------------------------------


def _header(config: IndexConfig) -> list[str]:
    lines = [
        "# 🪞 Mirrored 中文索引",
        "",
        GENERATED_NOTE,
        "",
        "开放模块与脚本的镜像，可直接用于 Surge / Egern / Loon / Stash / Quantumult X。",
        "",
    ]
    if config.about:
        lines += ["## 为什么是 Mirrored", ""]
        for paragraph in config.about:
            lines += [paragraph, ""]
    return lines


def _quick_start(root: Path, config: IndexConfig) -> list[str]:
    lines = ["## 🚀 快速开始", ""]
    for filename in config.pinned:
        path = root / config.modules_dir / filename
        if not path.is_file():
            continue
        entry = read_entry(path)
        lines += [
            f"**{cell(entry.name)}**（推荐的去广告合集）：",
            "",
            "```text",
            f"{config.raw_base}/{config.modules_dir}/{filename}",
            "```",
            "",
        ]
    lines += ["| App | 添加方式 |", "| --- | --- |"]
    lines += [f"| {FORMAT_LABELS[ext]} | {hint} |" for ext, hint in INSTALL_HINTS.items()]
    return [*lines, ""]


def _hidden(config: IndexConfig, *values: str) -> bool:
    text = " ".join(values).lower()
    return any(term in text for term in config.hide)


def _authors(authors: list[dict], config: IndexConfig) -> str:
    parts = []
    for author in authors:
        name, home = author.get("name", ""), author.get("homepage", "")
        if _hidden(config, name, home):
            continue
        name = cell(clean(name))
        parts.append(f"[{name}]({home})" if home.startswith("http") else name)
    return "、".join(parts) or "—"


def _date(value: str) -> str:
    # Non-breaking hyphens keep "2026-06-01" on one line in narrow columns.
    return value[:10].replace("-", "\u2011") or "—"


def _kelee(root: Path, config: IndexConfig) -> list[str]:
    catalog_path = root / config.catalog
    records = (
        json.loads(catalog_path.read_text(encoding="utf-8"))
        if catalog_path.is_file()
        else {"notice": [], "plugins": []}
    )
    modules = root / config.modules_dir
    available = [p for p in records.get("plugins", []) if (modules / p["file"]).is_file()]
    hidden = {
        p["file"] for p in available if _hidden(config, p["name"], p.get("desc", ""), p["file"])
    }
    plugins = [p for p in available if p["file"] not in hidden]

    by_tag: dict[str, list[dict]] = defaultdict(list)
    for plugin in plugins:
        by_tag[(plugin.get("tags") or [OTHER_GROUP])[0]].append(plugin)
    groups: dict[str, list[dict]] = defaultdict(list)
    for tag, items in by_tag.items():
        groups[tag if len(items) >= MIN_GROUP_SIZE else OTHER_GROUP].extend(items)

    lines = [
        f"## 🧩 去广告与工具模块 · {len(plugins)} 个",
        "",
        "点击名称打开模块链接。",
        "",
    ]

    # Different upstream plugins can share a display name.
    duplicates = _duplicates([clean(p["name"]) for p in plugins])

    # Largest groups first; the catch-all group always comes last.
    ordered = sorted(groups.items(), key=lambda kv: (kv[0] == OTHER_GROUP, -len(kv[1]), kv[0]))
    for tag, items in ordered:
        table = ["| | 名称 | 说明 | 作者 | 更新 |", "| :-: | --- | --- | --- | :-: |"]
        for p in items:
            icon = f'<img src="{p["icon"]}" width="24" alt="">' if p.get("icon") else ""
            url = f"{config.raw_base}/{config.modules_dir}/{p['file']}"
            name = clean(p["name"])
            label = _disambiguate(f"[{cell(name)}]({url})", name, Path(p["file"]).stem, duplicates)
            table.append(
                f"| {icon} | {label} "
                f"| {cell(clean(p.get('desc', ''), DESC_LIMIT)) or '—'} "
                f"| {_authors(p.get('authors', []), config)} | {_date(p.get('date', ''))} |"
            )
        summary = f"<b>{cell(tag)}</b> · {len(items)} 个"
        lines += _details(summary, table, open_=len(items) <= OPEN_GROUP_LIMIT)

    listed = {p["file"] for p in plugins} | hidden | set(config.pinned)
    others = [
        entry
        for path in sorted(modules.glob("*.sgmodule"), key=lambda p: p.name.lower())
        if path.name not in listed
        and not _hidden(config, (entry := read_entry(path)).name, entry.desc, entry.filename)
    ]
    if others:
        table = ["| 名称 | 说明 | 文件 |", "| --- | --- | --- |"]
        for e in others:
            url = f"{config.raw_base}/{config.modules_dir}/{e.filename}"
            table.append(f"| {cell(e.name)} | {cell(e.desc) or '—'} | [{e.filename}]({url}) |")
        summary = f"<b>其他模块</b> · {len(others)} 个（自维护或已下架）"
        lines += _details(summary, table, open_=False)
    return lines


def _project(root: Path, config: IndexConfig, project: IndexProject) -> list[str]:
    formats = [ext for ext in FORMAT_LABELS if ext in project.dirs]
    # Rows are keyed by file stem so each format of the same module shares a row.
    rows: dict[str, dict[str, Entry]] = defaultdict(dict)
    for ext in formats:
        for path in (root / project.dirs[ext]).glob(f"*.{ext}"):
            rows[path.stem][ext] = read_entry(path)

    lines = [f"## {project.title}", ""]
    intro = project.intro
    if project.upstream:
        intro = f"{intro} 上游：<{project.upstream}>" if intro else f"上游：<{project.upstream}>"
    if intro:
        lines += [intro, ""]
    lines += [
        "| 名称 | 说明 | " + " | ".join(FORMAT_LABELS[ext] for ext in formats) + " |",
        "| --- | --- | " + " | ".join(":-:" for _ in formats) + " |",
    ]

    def first_entry(stem: str) -> Entry:
        return rows[stem][next(ext for ext in formats if ext in rows[stem])]

    duplicates = _duplicates([first_entry(stem).name for stem in rows])
    for stem in sorted(rows, key=str.lower):
        by_ext = rows[stem]
        first = first_entry(stem)
        links = [
            f"[链接]({config.raw_base}/{project.dirs[ext]}/{by_ext[ext].filename})"
            if ext in by_ext
            else "—"
            for ext in formats
        ]
        label = _disambiguate(cell(first.name), first.name, stem, duplicates)
        lines.append("| " + " | ".join([label, cell(first.desc) or "—", *links]) + " |")
    return [*lines, ""]


def _footer(config: IndexConfig) -> list[str]:
    return [
        "## 📜 规则集与脚本",
        "",
        "- 去广告规则集："
        f"[`Chores/ruleset/reject.list`]({config.raw_base}/Chores/ruleset/reject.list)",
        "- 模块引用的外部脚本镜像：[`Chores/js/`](Chores/js)",
        "",
        "## ⚠️ 声明",
        "",
        "仅供学习与个人备份使用，所有模块与脚本的版权归原作者所有，"
        "每个文件开头的 `# 🪞 Mirrored` 注释标明了它的上游来源。"
        "如有侵权请提交 issue，将及时删除。",
    ]


def render(root: Path, config: IndexConfig) -> str:
    lines = _header(config) + _quick_start(root, config) + _kelee(root, config)
    for project in config.projects:
        lines += _project(root, config, project)
    lines += _footer(config)
    return "\n".join(lines).rstrip() + "\n"


def build(root: Path, config: IndexConfig) -> bool:
    """Write the index page; return whether it changed."""
    return write_if_changed(root / config.output, render(root, config).encode("utf-8"))
