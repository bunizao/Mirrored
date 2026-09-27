"""Validate the real config files shipped in the repository."""

from __future__ import annotations

from pathlib import Path

import pytest

from mirrored.config import ConfigError, load_aio, load_modules, load_releases

ROOT = Path(__file__).resolve().parents[1]


def test_releases_config_loads() -> None:
    sources = load_releases(ROOT / "config/releases.yaml")
    names = {s.name for s in sources}
    assert {"BiliUniverse", "DualSubs", "iRingo"} <= names
    for source in sources:
        assert source.repos, source.name
        for repo in source.repos:
            assert repo.count("/") == 1, repo


def test_modules_config_loads() -> None:
    config = load_modules(ROOT / "config/modules.yaml")
    assert config.catalog.urls
    assert all(ext.startswith(".") for ext in config.catalog.extensions)


def test_aio_config_points_at_existing_files() -> None:
    config = load_aio(ROOT / "config/aio.yaml")
    assert (ROOT / config.template).is_file()
    # Headers must stay strings even when they look like numbers (e.g. 12306).
    assert all(isinstance(s.header, str) for s in config.sources)
    missing = [s.path for s in config.sources if not (ROOT / s.path).is_file()]
    assert not missing, f"All-in-One sources missing from the repository: {missing}"


def test_invalid_config_reports_location(tmp_path: Path) -> None:
    path = tmp_path / "releases.yaml"
    path.write_text("sources:\n  - name: X\n    repos: [a/b]\n")
    with pytest.raises(ConfigError, match=r"sources\[0\].*routes"):
        load_releases(path)
