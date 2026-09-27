"""Test doubles for HTTP sessions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class FakeResponse:
    status_code: int = 200
    content: bytes = b""
    url: str = ""
    history: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self):
        import json

        return json.loads(self.content)


class FakeSession:
    """Minimal stand-in for ``requests.Session`` driven by a URL -> response mapping."""

    def __init__(
        self,
        routes: dict[str, FakeResponse | Exception | Callable[[], FakeResponse]],
        fallback: Callable[[str], FakeResponse] | None = None,
    ):
        self.routes = routes
        self.fallback = fallback
        self.headers: dict[str, str] = {}
        self.calls: list[str] = []

    def get(self, url: str, **_: object) -> FakeResponse:
        self.calls.append(url)
        route = self.routes.get(url)
        if route is None and self.fallback:
            return self.fallback(url)
        if route is None:
            return FakeResponse(404, b'{"message": "Not Found"}', url)
        if isinstance(route, Exception):
            raise route
        if callable(route):
            return route()
        return route
