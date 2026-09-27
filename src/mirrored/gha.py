"""GitHub Actions integration: annotations, log groups, step summaries and outputs.

Everything degrades to plain stdout when run outside of Actions.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager


def _escape(message: str) -> str:
    # Workflow commands require these characters to be percent-encoded.
    return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def notice(message: str) -> None:
    print(f"::notice::{_escape(message)}", flush=True)


def warning(message: str) -> None:
    print(f"::warning::{_escape(message)}", flush=True)


def error(message: str) -> None:
    print(f"::error::{_escape(message)}", flush=True)


@contextmanager
def group(title: str) -> Iterator[None]:
    print(f"::group::{title}", flush=True)
    try:
        yield
    finally:
        print("::endgroup::", flush=True)


def set_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def summary(markdown: str) -> None:
    """Append Markdown to the job summary, or print it when not in Actions."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        print(markdown)
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(markdown.rstrip() + "\n\n")


def table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Render a Markdown table; pipes inside cells are escaped."""

    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)
