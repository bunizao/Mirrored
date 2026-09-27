from __future__ import annotations

from mirrored.credit import CREDIT_PREFIX, add_credit


def test_credit_goes_after_the_metadata_header() -> None:
    module = "#!name=A\n#!desc=B\n\n[Rule]\nDOMAIN,a.example,REJECT\n"
    lines = add_credit(module, "https://up.example/A.lpx").split("\n")
    assert lines[:3] == [
        "#!name=A",
        "#!desc=B",
        f"{CREDIT_PREFIX} by https://github.com/bunizao/Mirrored · source: https://up.example/A.lpx",
    ]
    assert lines[3:] == ["", "[Rule]", "DOMAIN,a.example,REJECT", ""]


def test_credit_on_top_without_header_and_is_idempotent() -> None:
    override = 'name: "X"\nrules: []\n'
    once = add_credit(override, "https://up.example")
    assert once.startswith(CREDIT_PREFIX)
    assert add_credit(once, "https://up.example") == once
    # A changed source replaces the old credit instead of stacking a second one.
    moved = add_credit(once, "https://new.example")
    assert moved.count(CREDIT_PREFIX) == 1
    assert "https://new.example" in moved
