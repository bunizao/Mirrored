from __future__ import annotations

from pathlib import Path

from mirrored import index
from mirrored.config import IndexConfig, IndexPage, IndexSection, load_index

ROOT = Path(__file__).resolve().parents[1]


def test_read_metadata_handles_surge_and_stash_headers() -> None:
    surge = "#!name = 📺 BiliBili: 🌐 Global\n#!desc = 全球模式\\n全区搜索\n#!name=ignored\n"
    assert index.read_metadata(surge) == {
        "name": "📺 BiliBili: 🌐 Global",
        "desc": "全球模式\\n全区搜索",
    }

    stash = 'name: " iRingo: 🗺️ Maps"\ndesc: |-\n  自定义 Maps app\n  second line\nrules:\n'
    meta = index.read_metadata(stash)
    assert index.clean(meta["name"]) == "iRingo: 🗺️ Maps"
    assert meta["desc"].strip() == "自定义 Maps app"


def test_clean_flattens_and_truncates() -> None:
    assert index.clean("a\\nb   c") == "a b c"
    assert index.clean("x" * 10, limit=5) == "xxxx…"


def test_render_page_pins_escapes_and_links(tmp_path: Path) -> None:
    (tmp_path / "mods").mkdir()
    (tmp_path / "mods/B.sgmodule").write_text("#!name=Bee\n#!desc=a | b <c>\n")
    (tmp_path / "mods/A.sgmodule").write_text("#!name=Aye\n")
    (tmp_path / "mods/NoHeader.sgmodule").write_text("[Rule]\n")
    config = IndexConfig(
        raw_base="https://raw.example/main",
        root="README.zh-CN.md",
        pages=(
            IndexPage(
                path="mods",
                title="模块",
                intro="介绍",
                upstream="",
                sections=(IndexSection("mods", "sgmodule", "Surge 模块"),),
                pinned=("B.sgmodule",),
            ),
        ),
    )

    page = index.render_page(tmp_path, config.pages[0], config)

    assert "## Surge 模块（3 个）" in page
    pinned, rest = page.split("**推荐**")[1].split("| A", 1)
    assert "Bee" in pinned
    assert "a \\| b &lt;c&gt;" in pinned
    assert "[A.sgmodule](https://raw.example/main/mods/A.sgmodule)" in "| A" + rest
    assert "| NoHeader | — |" in rest

    changed = index.build(tmp_path, config)
    assert changed == ["README.zh-CN.md", "mods/README.md"]
    assert index.build(tmp_path, config) == []


def test_committed_index_pages_are_current() -> None:
    config = load_index(ROOT / "config/index.yaml")
    stale = [
        f"{page.path}/README.md"
        for page in config.pages
        if (ROOT / page.path / "README.md").read_text(encoding="utf-8")
        != index.render_page(ROOT, page, config)
    ]
    if (ROOT / config.root).read_text(encoding="utf-8") != index.render_root(config):
        stale.append(config.root)
    assert not stale, f"run `uv run mirrored build-index` to refresh: {stale}"
