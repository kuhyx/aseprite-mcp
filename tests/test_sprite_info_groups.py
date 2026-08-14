"""get_sprite_info enumerates nested (grouped) layers with a parent field."""

import json

from conftest import ok, run

from aseprite_mcp.tools import animation, canvas


def test_get_sprite_info_enumerates_group_children(sprite: str) -> None:
    ok(run(canvas.add_group(sprite, "grp")))
    ok(run(canvas.add_layer(sprite, "child", "grp")))
    layers = json.loads(run(animation.get_sprite_info(sprite)))["layers"]
    names = [item["name"] for item in layers]
    assert "grp" in names  # nested layer enumerated
    assert "child" in names
    child = next(item for item in layers if item["name"] == "child")
    assert child["parent"] == "grp"
    grp = next(item for item in layers if item["name"] == "grp")
    assert grp["is_group"] is True
    assert grp["parent"] is None
