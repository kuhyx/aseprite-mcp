"""Frame, cel, and tag tools added to animation.py."""

import json

from conftest import ok, run

from aseprite_mcp.tools import animation


def test_add_frames(sprite: str) -> None:
    ok(run(animation.add_frames(sprite, 3, 100)))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    assert info["frames"] == 4


def test_set_cel_opacity(sprite: str) -> None:
    ok(run(animation.set_cel_opacity(sprite, "body", 1, 200)))


def test_set_and_delete_tag(sprite: str) -> None:
    ok(run(animation.set_tag(sprite, "walk", 1, 3, "forward")))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    tag = next(t for t in info["tags"] if t["name"] == "walk")
    # Tag.fromFrame/toFrame must be the exact requested range (tag.md:
    # Tag.frames == toFrame.frameNumber - fromFrame.frameNumber + 1), not
    # clamped or off-by-one.
    assert (tag["from"], tag["to"]) == (1, 3)
    assert tag["direction"] == "forward"
    ok(run(animation.delete_tag(sprite, "walk")))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    assert info["tags"] == []


def test_delete_tag_missing(sprite: str) -> None:
    result = run(animation.delete_tag(sprite, "nope"))
    assert "Tag not found" in result


def test_delete_frame(sprite: str) -> None:
    ok(run(animation.delete_frame(sprite, 4)))
    info = json.loads(run(animation.get_sprite_info(sprite)))
    assert info["frames"] == 3
