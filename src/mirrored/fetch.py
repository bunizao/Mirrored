"""Download upstream files with a fallback chain: direct first, then through a proxy.

kelee.one only serves clients that identify as Surge and has also blocked
some networks outright, so each file is tried directly with the configured
User-Agent and, for configured hosts, again through ``PROXY_BASE``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.parse import urlparse

import requests


class FetchError(Exception):
    """Every strategy failed; the message lists why each one did."""


@dataclass(frozen=True)
class Fetched:
    content: bytes
    via: str  # "direct" or "proxy"


def matches_host(url: str, hosts: Sequence[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith(f".{h}") for h in hosts)


def fetch(
    session: requests.Session,
    url: str,
    *,
    proxy_base: str = "",
    proxy_hosts: Sequence[str] = (),
    validate: Callable[[bytes], bool] = bool,
    timeout: tuple[float, float] = (30, 60),
) -> Fetched:
    attempts = [("direct", url)]
    if proxy_base and matches_host(url, proxy_hosts):
        attempts.append(("proxy", f"{proxy_base}{url}"))

    reasons = []
    for via, target in attempts:
        try:
            response = session.get(target, timeout=timeout)
        except requests.RequestException as exc:
            reasons.append(f"{via}: {type(exc).__name__}")
            continue
        if response.status_code != 200:
            reasons.append(f"{via}: HTTP {response.status_code}")
        elif not validate(response.content):
            reasons.append(f"{via}: unexpected content")
        else:
            return Fetched(response.content, via)
    raise FetchError("; ".join(reasons))
