"""Merge several ad-blocking modules into the All-in-One module and a reject ruleset."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from mirrored.config import AioConfig
from mirrored.files import write_if_changed

# A `[Section]` header followed by everything up to the next line starting with `[`.
SECTION_RE = re.compile(r"\[(.*?)\]\s*\n(.*?)(?=\n\[|$)", re.DOTALL)
HOSTNAME_RE = re.compile(r"hostname\s*=\s*(.*)", re.IGNORECASE)
# Policies are stripped so the rules can be published as a plain reject list.
POLICY_RE = re.compile(
    r"(?:,\s*|-\s*)(REJECT(?:-(?:DROP|TINYGIF|NO-DROP))?|DIRECT)\b", re.IGNORECASE
)
UPDATE_DATE_RE = re.compile(r"(Update:\s*)(\d{2}/\d{2}/\d{4})")

# Sections copied into the template, in placeholder substitution order.
COPIED_SECTIONS = ("URL Rewrite", "Map Local", "Script")
DIVIDER_WIDTH = 30


class MissingSourceError(Exception):
    """A configured source module does not exist."""


@dataclass
class Merged:
    headers: list[str] = field(default_factory=list)
    sections: dict[str, list[str]] = field(
        default_factory=lambda: {name: [] for name in COPIED_SECTIONS}
    )
    rules: list[str] = field(default_factory=list)
    hostnames: list[str] = field(default_factory=list)


def divider(header: str) -> str:
    left = (DIVIDER_WIDTH - len(header)) // 2
    right = DIVIDER_WIDTH - len(header) - left
    return f"# {'-' * left} {header} {'-' * right}"


def merge_module(merged: Merged, header: str, content: str) -> None:
    merged.headers.append(header)
    for section, body in SECTION_RE.findall(content):
        if section == "Rule":
            merged.rules.append(POLICY_RE.sub("", body).strip())
        elif section in COPIED_SECTIONS:
            lines = [
                line
                for line in body.strip().splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            merged.sections[section].append(f"{divider(header)}\n" + "\n".join(lines))
        elif section == "MITM":
            match = HOSTNAME_RE.search(body)
            if match:
                hosts = match.group(1).replace("%APPEND%", "").split(",")
                merged.hostnames.extend(h.strip() for h in hosts if h.strip())


def render(template: str, merged: Merged, date: str) -> str:
    text = template
    for section in COPIED_SECTIONS:
        text = text.replace(f"{{{section}}}", "\n\n".join(merged.sections[section]))
    text = text.replace("{headers}", ", ".join(merged.headers))
    text = text.replace("{hostname_append}", ", ".join(dict.fromkeys(merged.hostnames)))
    return text.replace("{{currentDate}}", date)


def keep_previous_date(new: str, previous: str | None) -> str:
    """Reuse the old ``Update:`` date when nothing but the date would change.

    This keeps the generated file stable so scheduled runs do not create
    date-only commits.
    """
    if previous is None:
        return new
    old_date = UPDATE_DATE_RE.search(previous)
    if not old_date:
        return new
    if UPDATE_DATE_RE.sub(r"\1", new) != UPDATE_DATE_RE.sub(r"\1", previous):
        return new
    return UPDATE_DATE_RE.sub(lambda m: m.group(1) + old_date.group(2), new, count=1)


def load_sources(root: Path, config: AioConfig) -> Merged:
    missing: Sequence[str] = [s.path for s in config.sources if not (root / s.path).is_file()]
    if missing:
        raise MissingSourceError(", ".join(missing))
    merged = Merged()
    for source in config.sources:
        merge_module(merged, source.header, (root / source.path).read_text(encoding="utf-8"))
    return merged


def build(root: Path, config: AioConfig, *, date: str | None = None) -> dict[str, bool]:
    """Build the module and ruleset; return which output files changed."""
    merged = load_sources(root, config)
    date = date or datetime.now(UTC).strftime("%m/%d/%Y")
    template = (root / config.template).read_text(encoding="utf-8")

    output = root / config.output
    previous = output.read_text(encoding="utf-8") if output.is_file() else None
    module = keep_previous_date(render(template, merged, date), previous)

    return {
        config.output: write_if_changed(output, module.encode("utf-8")),
        config.ruleset: write_if_changed(
            root / config.ruleset, "\n".join(merged.rules).encode("utf-8")
        ),
    }
