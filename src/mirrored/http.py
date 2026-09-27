"""Shared HTTP session factory."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Errors worth retrying: rate limiting and gateway failures. Other 4xx/5xx
# responses are deterministic and retrying them only slows the run down.
RETRY_STATUSES = (429, 502, 503, 504)


def make_session(
    *,
    user_agent: str | None = None,
    retries: int = 2,
    backoff: float = 1.0,
) -> requests.Session:
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=RETRY_STATUSES,
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    if user_agent:
        session.headers["User-Agent"] = user_agent
    return session
