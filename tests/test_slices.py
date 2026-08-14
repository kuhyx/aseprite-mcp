"""Slice tools (slices.py)."""

import json

from conftest import ok, run

from aseprite_mcp.tools import slices


def test_create_slice(sprite: str) -> None:
    ok(run(slices.create_slice(sprite, "button", 4, 4, 16, 12)))


def test_create_slice_rejects_duplicate(sprite: str) -> None:
    result = run(slices.create_slice(sprite, "button", 0, 0, 8, 8))
    assert "already exists" in result


def test_set_slice_center(sprite: str) -> None:
    ok(run(slices.set_slice_center(sprite, "button", 4, 4, 8, 4)))


def test_set_slice_pivot(sprite: str) -> None:
    ok(run(slices.set_slice_pivot(sprite, "button", 8, 6)))


def test_list_slices(sprite: str) -> None:
    listed = json.loads(ok(run(slices.list_slices(sprite))))
    assert listed[0]["name"] == "button"
    assert listed[0]["center"]["width"] == 8
    assert listed[0]["pivot"] == {"x": 8, "y": 6}


def test_delete_slice(sprite: str) -> None:
    ok(run(slices.delete_slice(sprite, "button")))
    assert json.loads(run(slices.list_slices(sprite))) == []
