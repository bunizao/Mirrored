from __future__ import annotations

import json
from pathlib import Path

from mirrored import releases
from mirrored.config import ExtraFile, ReleaseSource

from fakes import FakeResponse

API = "https://api.github.com/repos"


def release(*assets: str, html_url: str = "https://github.com/o/r/releases/tag/v1") -> bytes:
    return json.dumps(
        {
            "html_url": html_url,
            "assets": [
                {"name": name, "browser_download_url": f"https://dl.example/{name}"}
                for name in assets
            ],
        }
    ).encode()


def test_apply_argument_overrides_matches_legacy_sed() -> None:
    text = "\n".join(
        [
            '#!arguments=Proxy:"🌑Proxy",CountryCode:"US"',
            "#!arguments-desc=Proxy: description stays",
            '#!arguments = Proxy:"spaced header is not touched"',
            "body Proxy:untouched",
        ]
    )
    result = releases.apply_argument_overrides(text, {"Proxy": "United States"})
    assert result.split("\n") == [
        '#!arguments=Proxy:United States,CountryCode:"US"',
        "#!arguments-desc=Proxy: description stays",
        '#!arguments = Proxy:"spaced header is not touched"',
        "body Proxy:untouched",
    ]


def test_extension_of() -> None:
    assert releases.extension_of("Siri.V2.beta.sgmodule") == "sgmodule"
    assert releases.extension_of("README") == "README"


def test_sync_routes_assets_and_follows_redirects(tmp_path: Path, fake_session) -> None:
    source = ReleaseSource(
        name="Demo",
        repos=("Old/Name",),
        routes={"sgmodule": "out/sg", "plugin": "out/plugin"},
        extra_files=(ExtraFile("https://raw.example/extra.sgmodule", "out/sg/extra.sgmodule"),),
        argument_overrides={"sgmodule": {"Proxy": "United States"}},
    )
    # The API answered through a redirect, as it does for renamed repositories.
    api = fake_session(
        {
            f"{API}/Old/Name/releases/latest": FakeResponse(
                content=release(
                    "A.sgmodule",
                    "A.plugin",
                    "notes.txt",
                    html_url="https://github.com/New/Name/releases/tag/v2",
                ),
                history=[FakeResponse(301)],
            )
        }
    )
    downloads = fake_session(
        {
            "https://dl.example/A.sgmodule": FakeResponse(content=b"#!arguments=Proxy:X\n"),
            "https://dl.example/A.plugin": FakeResponse(content=b"[Plugin]\n"),
            "https://raw.example/extra.sgmodule": FakeResponse(content=b"#!name=extra\n"),
        }
    )

    results = releases.sync_source(source, root=tmp_path, api=api, downloads=downloads)

    assert [r.error for r in results] == [None, None]
    assert results[0].updated == ["out/sg/A.sgmodule", "out/plugin/A.plugin"]
    assert (tmp_path / "out/sg/A.sgmodule").read_text() == "#!arguments=Proxy:United States\n"
    assert (tmp_path / "out/plugin/A.plugin").read_text() == "[Plugin]\n"
    assert (tmp_path / "out/sg/extra.sgmodule").exists()
    assert not (tmp_path / "out/notes.txt").exists()

    # A second run with identical upstream content changes nothing.
    again = releases.sync_source(source, root=tmp_path, api=api, downloads=downloads)
    assert [r.updated for r in again] == [[], []]


def test_one_failing_repo_does_not_stop_the_others(
    tmp_path: Path, fake_session, connection_error, capsys
) -> None:
    source = ReleaseSource(
        name="Demo", repos=("Gone/Repo", "Flaky/Repo", "Good/Repo"), routes={"sgmodule": "out"}
    )
    api = fake_session(
        {
            f"{API}/Flaky/Repo/releases/latest": connection_error,
            f"{API}/Good/Repo/releases/latest": FakeResponse(content=release("G.sgmodule")),
        }
    )
    downloads = fake_session({"https://dl.example/G.sgmodule": FakeResponse(content=b"g")})

    results = releases.sync_source(source, root=tmp_path, api=api, downloads=downloads)

    assert results[0].error == "HTTP 404: Not Found"
    assert results[1].error == "boom"
    assert results[2].updated == ["out/G.sgmodule"]
    assert "::warning::Gone/Repo: HTTP 404: Not Found" in capsys.readouterr().out


def test_failed_download_keeps_existing_file(tmp_path: Path, fake_session) -> None:
    (tmp_path / "out").mkdir()
    (tmp_path / "out/G.sgmodule").write_text("previous")
    source = ReleaseSource(name="Demo", repos=("Good/Repo",), routes={"sgmodule": "out"})
    api = fake_session(
        {f"{API}/Good/Repo/releases/latest": FakeResponse(content=release("G.sgmodule"))}
    )
    downloads = fake_session({"https://dl.example/G.sgmodule": FakeResponse(500)})

    results = releases.sync_source(source, root=tmp_path, api=api, downloads=downloads)

    assert results[0].error
    assert (tmp_path / "out/G.sgmodule").read_text() == "previous"
