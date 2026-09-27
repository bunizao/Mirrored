from __future__ import annotations

from pathlib import Path

import pytest

from mirrored import aio
from mirrored.config import AioConfig, AioSource

TEMPLATE = """#!name=AIO
#!desc=Update: {{currentDate}}
#!include={headers}, Extra
[Rule]
DOMAIN,keep.example,{{{Policy}}}

[URL Rewrite]
{URL Rewrite}

[Map Local]
{Map Local}

[Script]
{Script}

[MITM]
hostname = %APPEND% fixed.example, {hostname_append}
"""

MODULE_A = """#!name=A
[Rule]
DOMAIN,ads.a.example,REJECT
DOMAIN-SUFFIX,track.a.example,REJECT-DROP
DOMAIN,ok.a.example,DIRECT

[URL Rewrite]
# comment dropped
^https://a.example/ad - reject

[Script]
a = type=http-response,pattern=^https://a.example,script-path=https://x/a.js

[MITM]
hostname = %APPEND% a.example, shared.example
"""

MODULE_B = """#!name=B
[Map Local]
^https://b.example/ad data-type=text data="{}"

[MITM]
hostname = %APPEND% shared.example, b.example
"""


def make_repo(tmp_path: Path) -> AioConfig:
    (tmp_path / "config").mkdir()
    (tmp_path / "mods").mkdir()
    (tmp_path / "config/t.template").write_text(TEMPLATE)
    (tmp_path / "mods/a.sgmodule").write_text(MODULE_A)
    (tmp_path / "mods/b.sgmodule").write_text(MODULE_B)
    return AioConfig(
        template="config/t.template",
        output="out/aio.sgmodule",
        ruleset="out/reject.list",
        sources=(AioSource("mods/a.sgmodule", "A"), AioSource("mods/b.sgmodule", "Bee")),
    )


def test_divider_is_centred() -> None:
    assert aio.divider("AD Block") == "# ----------- AD Block -----------"
    assert len(aio.divider("Zhihu")) == len("# ") + 30 + 2


def test_build_merges_sections(tmp_path: Path) -> None:
    config = make_repo(tmp_path)
    changed = aio.build(tmp_path, config, date="01/02/2026")
    assert changed == {"out/aio.sgmodule": True, "out/reject.list": True}

    module = (tmp_path / "out/aio.sgmodule").read_text()
    assert "#!desc=Update: 01/02/2026" in module
    assert "#!include=A, Bee, Extra" in module
    assert "{{{Policy}}}" in module  # Surge argument placeholders survive.
    assert "# comment dropped" not in module
    assert f"{aio.divider('A')}\n^https://a.example/ad - reject" in module
    assert f"{aio.divider('Bee')}\n^https://b.example/ad" in module
    assert "fixed.example, a.example, shared.example, b.example\n" in module

    rules = (tmp_path / "out/reject.list").read_text()
    assert rules == ("DOMAIN,ads.a.example\nDOMAIN-SUFFIX,track.a.example\nDOMAIN,ok.a.example")


def test_date_only_change_keeps_previous_date(tmp_path: Path) -> None:
    config = make_repo(tmp_path)
    aio.build(tmp_path, config, date="01/02/2026")
    changed = aio.build(tmp_path, config, date="03/04/2026")
    assert changed == {"out/aio.sgmodule": False, "out/reject.list": False}
    assert "Update: 01/02/2026" in (tmp_path / "out/aio.sgmodule").read_text()


def test_content_change_bumps_date(tmp_path: Path) -> None:
    config = make_repo(tmp_path)
    aio.build(tmp_path, config, date="01/02/2026")
    (tmp_path / "mods/b.sgmodule").write_text(MODULE_B.replace("b.example/ad", "b.example/new"))
    aio.build(tmp_path, config, date="03/04/2026")
    assert "Update: 03/04/2026" in (tmp_path / "out/aio.sgmodule").read_text()


def test_missing_source_aborts_without_writing(tmp_path: Path) -> None:
    config = make_repo(tmp_path)
    (tmp_path / "mods/b.sgmodule").unlink()
    with pytest.raises(aio.MissingSourceError, match=r"mods/b\.sgmodule"):
        aio.build(tmp_path, config, date="01/02/2026")
    assert not (tmp_path / "out").exists()
