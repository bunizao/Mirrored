from __future__ import annotations

from pathlib import Path

from mirrored import catalog, convert, scripts
from mirrored.config import ConvertConfig, ScriptsConfig

from fakes import FakeResponse

CONVERT = ConvertConfig(
    output_dir="mods",
    scripthub_url="http://localhost:9101",
    category="🚫 AD Block",
    user_agent="Surge Mac/2985",
    proxy_hosts=("kelee.one",),
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
    url = convert.scripthub_url(
        "https://kelee.one/Tool/Loon/Lpx/1.1.1.1.lpx",
        "1.1.1.1",
        CONVERT,
        proxy_base="https://proxy.example?url=",
    )
    # Captured from a run of the previous shell implementation (proxy host replaced).
    assert url == (
        "http://localhost:9101/file/_start_/https://proxy.example?url="
        "https://kelee.one/Tool/Loon/Lpx/1.1.1.1.lpx/_end_/1.1.1.1.sgmodule"
        "?type=loon-plugin&target=surge-module&category=%F0%9F%9A%AB%20AD%20Block"
        "&headers=User-Agent%3A%20Surge%20Mac%2F2985"
    )


def test_proxy_only_applies_to_configured_hosts() -> None:
    assert convert.needs_proxy("https://sub.kelee.one/a.lpx", CONVERT.proxy_hosts)
    assert not convert.needs_proxy("https://notkelee.one/a.lpx", CONVERT.proxy_hosts)
    url = convert.scripthub_url("https://example.com/a.lpx", "a", CONVERT, proxy_base="P=")
    assert "_start_/https://example.com/a.lpx/_end_" in url


def test_failed_conversion_keeps_last_known_good_module(tmp_path: Path, fake_session) -> None:
    (tmp_path / "mods").mkdir()
    (tmp_path / "mods/Old.sgmodule").write_text("#!name=Old\nprevious\n")
    good = "https://example.com/New.lpx"
    blocked = "https://example.com/Old.lpx"
    session = fake_session(
        {
            convert.scripthub_url(good, "New", CONVERT): FakeResponse(content=b"#!name=New\n"),
            # Script-Hub reports an upstream 403 as a 500.
            convert.scripthub_url(blocked, "Old", CONVERT): FakeResponse(500),
        }
    )

    results = convert.convert_all(session, [good, blocked], root=tmp_path, config=CONVERT)

    assert {r.name: r.status for r in results} == {"New": "updated", "Old": "failed"}
    assert (tmp_path / "mods/Old.sgmodule").read_text() == "#!name=Old\nprevious\n"
    assert (tmp_path / "mods/New.sgmodule").read_text() == "#!name=New\n"


def test_non_module_response_is_rejected(tmp_path: Path, fake_session) -> None:
    url = "https://example.com/X.lpx"
    session = fake_session(
        {convert.scripthub_url(url, "X", CONVERT): FakeResponse(content=b"<html>error</html>")}
    )
    [result] = convert.convert_all(session, [url], root=tmp_path, config=CONVERT)
    assert result.status == "failed"
    assert not (tmp_path / "mods/X.sgmodule").exists()


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
