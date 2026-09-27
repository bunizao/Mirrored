from __future__ import annotations

import pytest
import requests

from fakes import FakeSession


@pytest.fixture
def fake_session() -> type[FakeSession]:
    return FakeSession


@pytest.fixture
def connection_error() -> requests.ConnectionError:
    return requests.ConnectionError("boom")
