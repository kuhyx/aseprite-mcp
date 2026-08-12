"""Layer management tools (layers.py)."""

from unittest.mock import patch

from conftest import ok, run

from aseprite_mcp.tools import canvas, drawing, layers


def test_rename_layer(sprite):
    ok(run(canvas.add_layer(sprite, "detail")))
    ok(run(drawing.draw_ellipse_at(sprite, "detail", 1, 16, 16, 6, 4, "#306230", True)))
    ok(run(layers.rename_layer(sprite, "detail", "shade")))


def test_duplicate_layer(sprite):
    result = ok(run(layers.duplicate_layer(sprite, "shade")))
    assert "shade copy" in result


def test_set_layer_blend_mode(sprite):
    ok(run(layers.set_layer_blend_mode(sprite, "shade copy", "multiply")))


def test_set_layer_blend_mode_rejects_unknown(sprite):
    result = run(layers.set_layer_blend_mode(sprite, "shade copy", "nonsense"))
    assert result.startswith("Unknown blend mode")


def test_reorder_layer(sprite):
    ok(run(layers.reorder_layer(sprite, "shade copy", 1)))


def test_merge_layer_down(sprite):
    ok(run(layers.merge_layer_down(sprite, "body")))


def test_delete_layer(sprite):
    ok(run(layers.delete_layer(sprite, "shade")))


def test_flatten_sprite(sprite):
    ok(run(layers.flatten_sprite(sprite)))


# ── file-not-found guards ───────────────────────────────────────────────


def test_delete_layer_missing_file():
    result = run(layers.delete_layer("/tmp/ase-pytest/does-not-exist.aseprite", "body"))
    assert result == "File /tmp/ase-pytest/does-not-exist.aseprite not found"


def test_rename_layer_missing_file():
    result = run(
        layers.rename_layer("/tmp/ase-pytest/does-not-exist.aseprite", "body", "x")
    )
    assert "not found" in result


def test_duplicate_layer_missing_file():
    result = run(
        layers.duplicate_layer("/tmp/ase-pytest/does-not-exist.aseprite", "body")
    )
    assert "not found" in result


def test_reorder_layer_missing_file():
    result = run(
        layers.reorder_layer("/tmp/ase-pytest/does-not-exist.aseprite", "body", 1)
    )
    assert "not found" in result


def test_set_layer_blend_mode_missing_file():
    result = run(
        layers.set_layer_blend_mode(
            "/tmp/ase-pytest/does-not-exist.aseprite", "body", "normal"
        )
    )
    assert "not found" in result


def test_merge_layer_down_missing_file():
    result = run(
        layers.merge_layer_down("/tmp/ase-pytest/does-not-exist.aseprite", "body")
    )
    assert "not found" in result


def test_flatten_sprite_missing_file():
    result = run(layers.flatten_sprite("/tmp/ase-pytest/does-not-exist.aseprite"))
    assert "not found" in result


# ── validation branches ─────────────────────────────────────────────────


def test_rename_layer_rejects_empty_new_name(sprite):
    result = run(layers.rename_layer(sprite, "body", ""))
    assert result == "New name cannot be empty"


def test_reorder_layer_rejects_position_below_one(sprite):
    result = run(layers.reorder_layer(sprite, "body", 0))
    assert result == "Position must be >= 1"


# ── "Failed to X" script-error branches ─────────────────────────────────
#
# These use a dedicated sprite (not the shared module-scoped `sprite`
# fixture) because by this point in the file the shared sprite has already
# been mutated by test_delete_layer/test_flatten_sprite etc., so a layer
# named "body" is no longer guaranteed to exist or to be in the bottom
# stack position.


def _fresh_sprite():
    path = "/tmp/ase-pytest/layers-errors.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    ok(run(canvas.add_layer(path, "body")))
    return path


def test_delete_layer_reports_layer_not_found():
    fresh = _fresh_sprite()
    result = run(layers.delete_layer(fresh, "no-such-layer"))
    assert result.startswith("Failed to delete layer:")


def test_delete_layer_reports_cannot_delete_only_layer():
    solo_path = "/tmp/ase-pytest/layers-solo.aseprite"
    ok(run(canvas.create_canvas(8, 8, solo_path)))
    result = run(layers.delete_layer(solo_path, "Layer 1"))
    assert result.startswith("Failed to delete layer:")
    assert "only layer" in result


def test_rename_layer_reports_layer_not_found():
    fresh = _fresh_sprite()
    result = run(layers.rename_layer(fresh, "no-such-layer", "whatever"))
    assert result.startswith("Failed to rename layer:")


def test_duplicate_layer_reports_layer_not_found():
    fresh = _fresh_sprite()
    result = run(layers.duplicate_layer(fresh, "no-such-layer"))
    assert result.startswith("Failed to duplicate layer:")


def test_duplicate_layer_reports_group_not_found():
    fresh = _fresh_sprite()
    result = run(
        layers.duplicate_layer(fresh, "body", "body copy 2", group="no-such-group")
    )
    assert result.startswith("Failed to duplicate layer:")


def test_duplicate_layer_into_group():
    fresh = _fresh_sprite()
    ok(run(canvas.add_group(fresh, "holder")))
    result = ok(
        run(layers.duplicate_layer(fresh, "body", "body in group", group="holder"))
    )
    assert "inside group 'holder'" in result


def test_reorder_layer_reports_layer_not_found():
    fresh = _fresh_sprite()
    result = run(layers.reorder_layer(fresh, "no-such-layer", 1))
    assert result.startswith("Failed to reorder layer:")


def test_reorder_layer_reports_position_out_of_range():
    fresh = _fresh_sprite()
    result = run(layers.reorder_layer(fresh, "body", 999))
    assert result.startswith("Failed to reorder layer:")
    assert "out of range" in result


def test_set_layer_blend_mode_reports_layer_not_found():
    fresh = _fresh_sprite()
    result = run(layers.set_layer_blend_mode(fresh, "no-such-layer", "normal"))
    assert result.startswith("Failed to set blend mode:")


def test_merge_layer_down_reports_layer_not_found():
    fresh = _fresh_sprite()
    result = run(layers.merge_layer_down(fresh, "no-such-layer"))
    assert result.startswith("Failed to merge layer down:")


def test_merge_layer_down_reports_bottom_layer_guard():
    # A freshly created sprite's single default layer is always the bottom
    # (and only) layer, so merging it down must hit the guard.
    solo_path = "/tmp/ase-pytest/layers-solo2.aseprite"
    ok(run(canvas.create_canvas(8, 8, solo_path)))
    result = run(layers.merge_layer_down(solo_path, "Layer 1"))
    assert result.startswith("Failed to merge layer down:")
    assert "bottom layer" in result


def test_flatten_sprite_reports_subprocess_failure(sprite):
    with patch(
        "aseprite_mcp.tools.layers.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(layers.flatten_sprite(sprite))
    assert result == "Failed to flatten sprite: boom"
