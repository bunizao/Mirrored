from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from mirrored import catalog, index
from mirrored.config import IndexConfig, IndexProject, load_index

ROOT = Path(__file__).resolve().parents[1]


def test_read_metadata_handles_surge_and_stash_headers() -> None:
    surge = "#!name = 📺 BiliBili: 🌐 Global\n#!desc = 全球模式\\n全区搜索\n#!name=ignored\n"
    assert index.read_metadata(surge) == {
        "name": "📺 BiliBili: 🌐 Global",
        "desc": "全球模式\\n全区搜索",
    }

    stash = 'name: " iRingo: 🗺️ Maps"\ndesc: |-\n  自定义 Maps app\n  second line\nrules:\n'
    meta = index.read_metadata(stash)
    # The Apple logo is a private-use glyph and is dropped from the page.
    assert index.clean(meta["name"]) == "iRingo: 🗺️ Maps"
    assert meta["desc"].strip() == "自定义 Maps app"


def test_clean_flattens_and_truncates() -> None:
    assert index.clean("a\\nb   c") == "a b c"
    assert index.clean("x" * 10, limit=5) == "xxxx…"


def test_plugin_records_map_catalog_entries_to_module_files() -> None:
    payload = {
        "name": "插件中心",
        "notice": ["声明"],
        "lists": [
            {
                "name": "12306去广告",
                "desc": "过滤广告",
                "tag": ["去广告"],
                "icon": "https://i.example/12306.png",
                "date": "2026-06-01 17:11:35",
                "url": "loon://import?plugin=https://kelee.one/Tool/Loon/Lpx/12306_remove_ads.lpx",
                "author": [{"name": "RuCu6", "homepage": "https://github.com/RuCu6"}],
            },
            {"name": "not a plugin", "url": "https://example.com/page"},
        ],
    }
    records = catalog.plugin_records(payload, [".lpx"])
    assert records["notice"] == ["声明"]
    assert records["plugins"] == [
        {
            "file": "12306_remove_ads.sgmodule",
            "name": "12306去广告",
            "desc": "过滤广告",
            "tags": ["去广告"],
            "icon": "https://i.example/12306.png",
            "date": "2026-06-01 17:11:35",
            "authors": [{"name": "RuCu6", "homepage": "https://github.com/RuCu6"}],
            "source": "https://kelee.one/Tool/Loon/Lpx/12306_remove_ads.lpx",
        }
    ]


def make_repo(tmp_path: Path) -> IndexConfig:
    mods = tmp_path / "mods"
    mods.mkdir()
    for name in ("Ad1", "Ad2", "Ad3", "Tool"):
        (mods / f"{name}.sgmodule").write_text(f"#!name={name}\n")
    (mods / "AIO.sgmodule").write_text("#!name=All in One\n")
    (mods / "Local.sgmodule").write_text("#!name=Local | module\n#!desc=<b>hand made</b>\n")
    plugins = [
        {"file": f"{n}.sgmodule", "name": n, "desc": "", "tags": [t], "icon": "", "date": d}
        for n, t, d in [
            ("Ad1", "去广告", "2026-06-01 00:00:00"),
            ("Ad2", "去广告", ""),
            ("Ad3", "去广告", ""),
            ("Tool", "签到", ""),
            ("Missing", "去广告", ""),  # Never converted: left out of the page.
        ]
    ]
    (tmp_path / "catalog.json").write_text(json.dumps({"notice": [], "plugins": plugins}))

    proj = tmp_path / "proj"
    for sub, ext in (("sg", "sgmodule"), ("st", "stoverride")):
        (proj / sub).mkdir(parents=True)
        (proj / sub / f"Maps.{ext}").write_text("#!name=Maps\n" if ext == "sgmodule" else "")
    (proj / "sg" / "News.sgmodule").write_text("#!name=News\n")

    return IndexConfig(
        output="INDEX.md",
        raw_base="https://raw.example/main",
        repo_url="https://github.com/o/r",
        catalog="catalog.json",
        modules_dir="mods",
        pinned=("AIO.sgmodule",),
        projects=(
            IndexProject(
                title="Proj",
                intro="",
                upstream="https://github.com/up",
                dirs={"sgmodule": "proj/sg", "stoverride": "proj/st"},
            ),
        ),
    )


def test_render_groups_catalog_plugins_and_lists_the_rest(tmp_path: Path) -> None:
    config = make_repo(tmp_path)
    page = index.render(tmp_path, config)

    assert "https://raw.example/main/mods/AIO.sgmodule" in page.split("## 🧩")[0]
    assert "## 🧩 去广告与工具模块 · 4 个" in page
    # 去广告 has 3 plugins and keeps its own group; 签到 (1) folds into 其他.
    assert "<summary><b>去广告</b> · 3 个</summary>" in page
    assert "<summary><b>其他</b> · 1 个</summary>" in page
    assert page.index("去广告</b>") < page.index("<b>其他</b>")
    assert "2026‑06‑01" in page
    assert "Missing" not in page
    # Files not in the catalog (and not pinned) are listed separately, escaped.
    others = page.split("<b>其他模块</b>")[1]
    assert "Local \\| module" in others
    assert "&lt;b&gt;hand made&lt;/b&gt;" in others
    assert "AIO.sgmodule" not in others


def test_render_merges_formats_of_a_project_into_one_row(tmp_path: Path) -> None:
    config = make_repo(tmp_path)
    page = index.render(tmp_path, config)
    section = page.split("## Proj")[1].split("## ")[0]
    assert "上游：<https://github.com/up>" in section
    assert "| 名称 | 说明 | Surge / Egern | Stash |" in section
    assert (
        "| Maps | — | [链接](https://raw.example/main/proj/sg/Maps.sgmodule) "
        "| [链接](https://raw.example/main/proj/st/Maps.stoverride) |"
    ) in section
    assert "| News | — | [链接](https://raw.example/main/proj/sg/News.sgmodule) | — |" in section

    assert index.build(tmp_path, config) is True
    assert index.build(tmp_path, config) is False


def test_same_name_modules_are_disambiguated_by_file(tmp_path: Path) -> None:
    config = make_repo(tmp_path)
    records = json.loads((tmp_path / "catalog.json").read_text())
    records["plugins"][1]["name"] = records["plugins"][2]["name"] = "Same"
    (tmp_path / "catalog.json").write_text(json.dumps(records))

    page = index.render(tmp_path, config)

    assert "Same.sgmodule" not in page
    assert "[Same](https://raw.example/main/mods/Ad2.sgmodule) <sub>Ad2</sub>" in page
    assert "[Same](https://raw.example/main/mods/Ad3.sgmodule) <sub>Ad3</sub>" in page
    assert "<sub>Ad1</sub>" not in page


def test_hidden_terms_drop_authors_and_plugins(tmp_path: Path) -> None:
    config = make_repo(tmp_path)
    records = json.loads((tmp_path / "catalog.json").read_text())
    records["plugins"][0]["authors"] = [
        {"name": "Alice", "homepage": "https://a.example"},
        {"name": "Blocked One", "homepage": "https://blocked.example"},
        {"name": "NoHome", "homepage": "None"},
    ]
    records["plugins"][1]["desc"] = "made by blocked"
    (tmp_path / "catalog.json").write_text(json.dumps(records))

    page = index.render(tmp_path, replace(config, hide=("blocked",)))

    assert "blocked" not in page.lower()
    assert "[Alice](https://a.example)、NoHome" in page
    # The hidden plugin is gone entirely, not moved to "other modules".
    assert "Ad2" not in page


def test_committed_index_page_is_current() -> None:
    config = load_index(ROOT / "config/index.yaml")
    committed = (ROOT / config.output).read_text(encoding="utf-8")
    assert committed == index.render(ROOT, config), "run `uv run mirrored build-index`"
