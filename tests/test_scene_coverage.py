"""Coverage gaps in scene.py (copy_layers_between_sprites) not hit by
test_error_propagation.py: missing source/target files, empty layer list,
the all-layers-present success path (no "MISSING:" line), and the
traversal guard.

Note: reject_traversal runs AFTER both os.path.exists checks in
copy_layers_between_sprites, and os.path.normpath collapses "x/../y" before
the ".." check ever sees it, so an absolute path can never trigger the
guard for a file that exists. The only way in is a relative path that
walks above cwd (os.path.relpath keeps a leading ".." through normpath).
"""

import os

import pytest

from conftest import BASE, ok, run

from aseprite_mcp.tools import canvas, scene


def test_copy_layers_missing_source(base_dir):
    target = f"{BASE}/scene_cov_target1.aseprite"
    ok(run(canvas.create_canvas(16, 16, target)))
    result = run(
        scene.copy_layers_between_sprites(
            "/tmp/ase-pytest/nope_source.aseprite", target, ["body"]
        )
    )
    assert "not found" in result


def test_copy_layers_missing_target(sprite):
    result = run(
        scene.copy_layers_between_sprites(
            sprite, "/tmp/ase-pytest/nope_target.aseprite", ["body"]
        )
    )
    assert "not found" in result


def test_copy_layers_empty_names(sprite, base_dir):
    target = f"{BASE}/scene_cov_target2.aseprite"
    ok(run(canvas.create_canvas(16, 16, target)))
    result = run(scene.copy_layers_between_sprites(sprite, target, []))
    assert "cannot be empty" in result


def test_copy_layers_all_present_no_missing_note(sprite, base_dir):
    target = f"{BASE}/scene_cov_target3.aseprite"
    ok(run(canvas.create_canvas(16, 16, target)))
    result = ok(run(scene.copy_layers_between_sprites(sprite, target, ["body"])))
    assert "skipped missing layers" not in result


def test_copy_layers_rejects_traversal(sprite, base_dir):
    target = f"{BASE}/scene_cov_target4.aseprite"
    ok(run(canvas.create_canvas(16, 16, target)))
    traversal_source = os.path.relpath(sprite)
    if ".." not in traversal_source.split(os.sep):
        pytest.skip(f"cwd {os.getcwd()!r} yields no '..' in relpath")
    result = run(scene.copy_layers_between_sprites(traversal_source, target, ["body"]))
    assert "Invalid" in result
