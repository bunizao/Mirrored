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
    user_agents: Sequence[str] = (),
    proxy_session: requests.Session | None = None,
    validate: Callable[[bytes], bool] = bool,
    timeout: tuple[float, float] = (30, 60),
) -> Fetched:
    """Try ``url`` directly with each of ``user_agents`` (or the session's), then the proxy.

    ``proxy_session`` (e.g. a browser-like session) is used for the proxy hop with
    its own User-Agent; otherwise ``session`` is reused with the first agent.
    """
    agents = list(user_agents) or [None]
    attempts = [
        ("direct" if i == 0 else f"direct#{i + 1}", session, url, agent)
        for i, agent in enumerate(agents)
    ]
    if proxy_base and matches_host(url, proxy_hosts):
        hop = (proxy_session, None) if proxy_session else (session, agents[0])
        attempts.append(("proxy", hop[0], f"{proxy_base}{url}", hop[1]))

    reasons = []
    for via, client, target, agent in attempts:
        headers = {"User-Agent": agent} if agent else None
        try:
            response = client.get(target, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            reasons.append(f"{via}: {type(exc).__name__}")
            continue
        if response.status_code != 200:
            reasons.append(f"{via}: HTTP {response.status_code}{_origin(response)}")
        elif not validate(response.content):
            reasons.append(f"{via}: unexpected content")
        else:
            return Fetched(response.content, via)
    raise FetchError("; ".join(reasons))


def _origin(response: requests.Response) -> str:
    # Naming the responding server (and Cloudflare's mitigation, if any) tells a
    # CDN/WAF block apart from the origin refusing.
    parts = [response.headers.get("Server", ""), response.headers.get("cf-mitigated", "")]
    details = ", ".join(p for p in parts if p)
    return f" ({details})" if details else ""
