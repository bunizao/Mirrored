from __future__ import annotations

import re
from pathlib import Path

import pytest
import requests

from mirrored import catalog, convert, fetch, scripts
from mirrored.config import ConvertConfig, ScriptsConfig

from fakes import FakeResponse

CONVERT = ConvertConfig(
    output_dir="mods",
    scripthub_url="http://localhost:9101",
    category="🚫 AD Block",
    user_agent="Surge Mac/2985",
    fetch_user_agents=("Surge Mac/2985",),
    proxy_hosts=("kelee.one",),
    serve_host="127.0.0.1",
)
SCRIPTS = ScriptsConfig(
    output_dir="js",
    mirror_base="https://mirror.example/js",
    user_agent="Surge Mac/3272",
    skip_patterns=("mirror.example",),
    exclude=("All-in-One.sgmodule",),
)


# --- catalog ---------------------------------------------------------------


def test_extract_plugin_urls_walks_nested_json_and_loon_links() -> None:
    payload = {
        "list": [
            {"url": "https://kelee.one/Tool/Loon/Lpx/A.lpx"},
            {"install": "loon://import?plugin=https%3A%2F%2Fexample.com%2FB.plugin"},
            {"icon": "https://example.com/icon.png"},
            ["https://example.com/C.LPX?raw=1", 42, None],
        ]
    }
    assert catalog.extract_plugin_urls(payload, [".lpx", "plugin"]) == [
        "https://example.com/B.plugin",
        "https://example.com/C.LPX?raw=1",
        "https://kelee.one/Tool/Loon/Lpx/A.lpx",
    ]


# --- conversion ------------------------------------------------------------


def test_plugin_name() -> None:
    assert convert.plugin_name("https://h/x/Foo_remove_ads.lpx?v=1#x") == "Foo_remove_ads"
    assert convert.plugin_name("https://h/x/1.1.1.1.plugin") == "1.1.1.1"


def test_scripthub_url_matches_legacy_workflow() -> None:
    url = convert.scripthub_url("https://kelee.one/Tool/Loon/Lpx/1.1.1.1.lpx", "1.1.1.1", CONVERT)
    # Same shape as the URLs the previous shell implementation produced.
    assert url == (
        "http://localhost:9101/file/_start_/"
        "https://kelee.one/Tool/Loon/Lpx/1.1.1.1.lpx/_end_/1.1.1.1.sgmodule"
        "?type=loon-plugin&target=surge-module&category=%F0%9F%9A%AB%20AD%20Block"
        "&headers=User-Agent%3A%20Surge%20Mac%2F2985"
    )


def fake_scripthub(fail: set[str] = frozenset()):
    """Script-Hub stand-in: fetches the plugin from the local server like the real one."""

    def handle(url: str) -> FakeResponse:
        source = re.search(r"_start_/(.*)/_end_/", url).group(1)
        assert source.startswith("http://127.0.0.1:"), source
        name = source.rsplit("/", 1)[-1]
        if name in fail:
            return FakeResponse(500, b"Error: conversion failed")
        plugin = requests.get(source, timeout=5)
        assert plugin.status_code == 200
        return FakeResponse(content=plugin.content + b"# converted\n")

    return handle


def test_convert_uses_fallback_and_keeps_last_known_good(tmp_path: Path, fake_session) -> None:
    (tmp_path / "mods").mkdir()
    (tmp_path / "mods/Gone.sgmodule").write_text("#!name=Gone\nprevious\n")
    (tmp_path / "mods/Broken.sgmodule").write_text("#!name=Broken\nprevious\n")
    direct = "https://kelee.one/p/Direct.lpx"
    proxied = "https://kelee.one/p/Proxied.lpx"
    gone = "https://kelee.one/p/Gone.lpx"
    broken = "https://example.com/Broken.plugin"
    downloads = fake_session(
        {
            direct: FakeResponse(content=b"#!name=Direct\n"),
            proxied: FakeResponse(403),
            f"P={proxied}": FakeResponse(content=b"#!name=Proxied\n"),
            gone: FakeResponse(403),
            f"P={gone}": FakeResponse(content=b"<html>blocked</html>"),
            broken: FakeResponse(content=b"#!name=Broken\n"),
        }
    )
    scripthub = fake_session({}, fallback=fake_scripthub(fail={"Broken.plugin"}))

    results = convert.convert_all(
        downloads,
        scripthub,
        [direct, proxied, gone, broken],
        root=tmp_path,
        config=CONVERT,
        proxy_base="P=",
    )

    by_name = {r.name: r for r in results}
    assert {n: (r.status, r.via) for n, r in by_name.items()} == {
        "Broken": ("failed", "direct"),
        "Direct": ("converted", "direct"),
        "Gone": ("failed", ""),
        "Proxied": ("converted", "proxy"),
    }
    assert by_name["Gone"].detail == "fetch: direct: HTTP 403; proxy: unexpected content"
    assert by_name["Broken"].detail == "convert: HTTP 500"
    assert (tmp_path / "mods/Direct.sgmodule").read_text() == "#!name=Direct\n# converted\n"
    assert (tmp_path / "mods/Proxied.sgmodule").read_text() == "#!name=Proxied\n# converted\n"
    assert (tmp_path / "mods/Gone.sgmodule").read_text() == "#!name=Gone\nprevious\n"
    assert (tmp_path / "mods/Broken.sgmodule").read_text() == "#!name=Broken\nprevious\n"


# --- fetch fallback --------------------------------------------------------


def test_fetch_prefers_direct_and_only_proxies_configured_hosts(
    fake_session, connection_error
) -> None:
    session = fake_session(
        {
            "https://kelee.one/a.js": connection_error,
            "P=https://kelee.one/a.js": FakeResponse(content=b"proxied"),
            "https://other.example/b.js": FakeResponse(403),
            "P=https://other.example/b.js": FakeResponse(content=b"never used"),
        }
    )
    got = fetch.fetch(session, "https://kelee.one/a.js", proxy_base="P=", proxy_hosts=["kelee.one"])
    assert got == fetch.Fetched(b"proxied", "proxy")
    with pytest.raises(fetch.FetchError, match=r"^direct: HTTP 403$"):
        fetch.fetch(
            session, "https://other.example/b.js", proxy_base="P=", proxy_hosts=["kelee.one"]
        )
    assert "P=https://other.example/b.js" not in session.calls


def test_fetch_tries_each_user_agent_and_names_the_blocker(fake_session) -> None:
    session = fake_session({}, fallback=lambda url: FakeResponse(403, headers={"Server": "cf"}))
    with pytest.raises(fetch.FetchError) as info:
        fetch.fetch(
            session,
            "https://kelee.one/a.lpx",
            proxy_base="P=",
            proxy_hosts=["kelee.one"],
            user_agents=["UA1", "UA2"],
        )
    assert [h["User-Agent"] for h in session.sent_headers] == ["UA1", "UA2", "UA1"]
    assert session.calls[-1] == "P=https://kelee.one/a.lpx"
    assert str(info.value) == "direct: HTTP 403 (cf); direct#2: HTTP 403 (cf); proxy: HTTP 403 (cf)"


def test_matches_host() -> None:
    assert fetch.matches_host("https://sub.kelee.one/a.lpx", ["kelee.one"])
    assert not fetch.matches_host("https://notkelee.one/a.lpx", ["kelee.one"])


# --- script mirroring ------------------------------------------------------


def test_script_filename() -> None:
    assert scripts.script_filename("https://h/a/b.js?x=1") == "b.js"
    assert scripts.script_filename("https://h/a/data.json") == "data.json.js"


def test_find_script_urls() -> None:
    text = (
        "a = type=http-response,script-path=https://h/a.js?v=2,requires-body=1\n"
        "b = type=cron,script-path = https://h/b.js\n"
        "c = script-path=https://mirror.example/js/c.js\n"
    )
    assert scripts.find_script_urls([text], SCRIPTS.skip_patterns) == [
        "https://h/a.js?v=2",
        "https://h/b.js",
    ]


def test_mirror_scripts_downloads_and_rewrites(tmp_path: Path, fake_session) -> None:
    mods = tmp_path / "mods"
    mods.mkdir()
    (mods / "M.sgmodule").write_text(
        "x = script-path=https://h/ok.js\n"
        "y = script-path=https://h/missing.js\n"
        "z = script-path=https://other/ok.js\n"
    )
    (mods / "All-in-One.sgmodule").write_text("x = script-path=https://h/ok.js\n")
    session = fake_session(
        {
            "https://h/ok.js": FakeResponse(content=b"console.log('ok');"),
            "https://other/ok.js": FakeResponse(content=b"console.log('other');"),
        }
    )

    results = scripts.mirror_scripts(session, root=tmp_path, modules_dir=mods, config=SCRIPTS)

    by_url = {r.url: r.status for r in results}
    assert by_url == {
        "https://h/ok.js": "updated",
        "https://h/missing.js": "failed",
        "https://other/ok.js": "skipped",  # Same file name as h/ok.js.
    }
    assert (tmp_path / "js/ok.js").read_bytes() == b"console.log('ok');"
    assert (mods / "M.sgmodule").read_text() == (
        "x = script-path=https://mirror.example/js/ok.js\n"
        "y = script-path=https://h/missing.js\n"
        "z = script-path=https://other/ok.js\n"
    )
    # Excluded modules are never rewritten.
    assert "https://h/ok.js" in (mods / "All-in-One.sgmodule").read_text()
