"""Credit line stamped into every mirrored module, plugin and override."""

from __future__ import annotations

MIRROR_URL = "https://github.com/bunizao/Mirrored"
CREDIT_PREFIX = "# 🪞 Mirrored"


def add_credit(text: str, source: str) -> str:
    """Insert the credit comment right after the ``#!`` metadata header.

    Files without such a header (e.g. Stash YAML overrides) get it on the first
    line. Any existing credit line is replaced, so repeated syncs are stable.
    """
    lines = [line for line in text.split("\n") if not line.startswith(CREDIT_PREFIX)]
    position = 0
    while position < len(lines) and lines[position].startswith("#!"):
        position += 1
    lines.insert(position, f"{CREDIT_PREFIX} by {MIRROR_URL} · source: {source}")
    return "\n".join(lines)


def add_credit_bytes(data: bytes, source: str) -> bytes:
    # surrogateescape round-trips any bytes that are not valid UTF-8 untouched.
    text = data.decode("utf-8", "surrogateescape")
    return add_credit(text, source).encode("utf-8", "surrogateescape")
