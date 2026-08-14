"""Coverage tests for canvas.py: layer/frame/group management tools."""

from pathlib import Path
from unittest.mock import patch

from conftest import BASE, ok, run

from aseprite_mcp.tools import canvas

_MOCK_PATH = "aseprite_mcp.tools.canvas.AsepriteCommand.execute_lua_script_checked"


# ── create_canvas ────────────────────────────────────────────────────────


def test_create_canvas_rejects_non_positive_dimensions() -> None:
    result = run(canvas.create_canvas(0, 10, f"{BASE}/bad_w.aseprite"))
    assert result == "Width and height must be > 0"

    result = run(canvas.create_canvas(10, -1, f"{BASE}/bad_h.aseprite"))
    assert result == "Width and height must be > 0"


def test_create_canvas_rejects_traversal() -> None:
    result = run(canvas.create_canvas(8, 8, "../evil.aseprite"))
    assert result == "Invalid filename: parent directory traversal not allowed"


def test_create_canvas_success() -> None:
    path = f"{BASE}/canvas_create.aseprite"
    result = ok(run(canvas.create_canvas(16, 16, path)))
    assert "Canvas created successfully" in result


def test_create_canvas_auto_creates_missing_parent_dir() -> None:
    # Sprite:saveAs() auto-creates missing parent directories rather than
    # failing (verified directly against real Aseprite) - so this does NOT
    # hit the "Failed to create canvas" branch.
    new_path = f"{BASE}/no-such-subdir/canvas.aseprite"
    result = run(canvas.create_canvas(8, 8, new_path))
    assert result.startswith("Canvas created successfully:")
    assert Path(new_path).exists()


# ── add_layer / add_group: missing-file guards ──────────────────────────


def test_add_layer_missing_file() -> None:
    result = run(canvas.add_layer(f"{BASE}/does-not-exist.aseprite", "body"))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_add_group_missing_file() -> None:
    result = run(canvas.add_group(f"{BASE}/does-not-exist.aseprite", "grp"))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_add_frame_missing_file() -> None:
    result = run(canvas.add_frame(f"{BASE}/does-not-exist.aseprite"))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_set_frame_missing_file() -> None:
    result = run(canvas.set_frame(f"{BASE}/does-not-exist.aseprite", 1))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_set_frame_duration_missing_file() -> None:
    result = run(canvas.set_frame_duration(f"{BASE}/does-not-exist.aseprite", 1, 100))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_set_layer_missing_file() -> None:
    result = run(canvas.set_layer(f"{BASE}/does-not-exist.aseprite", "body"))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


# ── set_frame_duration validation ───────────────────────────────────────


def test_set_frame_duration_rejects_non_positive(sprite: str) -> None:
    result = run(canvas.set_frame_duration(sprite, 1, 0))
    assert result == "Duration must be > 0"

    result = run(canvas.set_frame_duration(sprite, 1, -5))
    assert result == "Duration must be > 0"


# ── add_layer / add_group: happy paths and group handling ──────────────


def _fresh_sprite(name: str) -> str:
    path = f"{BASE}/{name}.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    ok(run(canvas.add_layer(path, "body")))
    return path


def test_add_layer_success() -> None:
    fresh = _fresh_sprite("canvas-add-layer")
    result = ok(run(canvas.add_layer(fresh, "extra")))
    assert "Layer 'extra' added" in result


def test_add_group_success() -> None:
    fresh = _fresh_sprite("canvas-add-group")
    result = ok(run(canvas.add_group(fresh, "holder")))
    assert "Group 'holder' created" in result


def test_add_group_nested_in_parent() -> None:
    fresh = _fresh_sprite("canvas-add-group-nested")
    ok(run(canvas.add_group(fresh, "outer")))
    result = ok(run(canvas.add_group(fresh, "inner", parent_group="outer")))
    assert "inside 'outer'" in result


def test_add_layer_into_group() -> None:
    fresh = _fresh_sprite("canvas-add-layer-group")
    ok(run(canvas.add_group(fresh, "holder")))
    result = ok(run(canvas.add_layer(fresh, "in-group", group="holder")))
    assert "inside group 'holder'" in result


def test_add_layer_reports_group_not_found() -> None:
    fresh = _fresh_sprite("canvas-add-layer-no-group")
    result = run(canvas.add_layer(fresh, "orphan", group="no-such-group"))
    assert result.startswith("Failed to add layer:")


def test_add_layer_reports_target_not_a_group() -> None:
    fresh = _fresh_sprite("canvas-add-layer-not-group")
    result = run(canvas.add_layer(fresh, "child", group="body"))
    assert result.startswith("Failed to add layer:")


def test_add_group_reports_parent_not_found() -> None:
    fresh = _fresh_sprite("canvas-add-group-no-parent")
    result = run(canvas.add_group(fresh, "grp", parent_group="no-such-group"))
    assert result.startswith("Failed to create group:")


def test_add_group_reports_target_not_a_group() -> None:
    fresh = _fresh_sprite("canvas-add-group-not-group")
    result = run(canvas.add_group(fresh, "grp", parent_group="body"))
    assert result.startswith("Failed to create group:")


# ── add_frame ─────────────────────────────────────────────────────────


def test_add_frame_success() -> None:
    fresh = _fresh_sprite("canvas-add-frame")
    result = ok(run(canvas.add_frame(fresh)))
    assert "New frame added successfully" in result


# ── set_frame ─────────────────────────────────────────────────────────


def test_set_frame_success() -> None:
    fresh = _fresh_sprite("canvas-set-frame")
    ok(run(canvas.add_frame(fresh)))
    result = ok(run(canvas.set_frame(fresh, 2)))
    assert "Active frame set to 2" in result


def test_set_frame_reports_out_of_range() -> None:
    fresh = _fresh_sprite("canvas-set-frame-oob")
    result = run(canvas.set_frame(fresh, 999))
    assert result.startswith("Failed to set frame:")
    assert "out of range" in result


def test_set_frame_reports_zero_index_out_of_range() -> None:
    fresh = _fresh_sprite("canvas-set-frame-zero")
    result = run(canvas.set_frame(fresh, 0))
    assert result.startswith("Failed to set frame:")


# ── set_frame_duration success / error ──────────────────────────────────


def test_set_frame_duration_success() -> None:
    fresh = _fresh_sprite("canvas-frame-duration")
    result = ok(run(canvas.set_frame_duration(fresh, 1, 250)))
    assert "duration set to 250ms" in result


def test_set_frame_duration_reports_out_of_range() -> None:
    fresh = _fresh_sprite("canvas-frame-duration-oob")
    result = run(canvas.set_frame_duration(fresh, 999, 100))
    assert result.startswith("Failed to set frame duration:")


# ── set_layer ────────────────────────────────────────────────────────


def test_set_layer_success_existing() -> None:
    fresh = _fresh_sprite("canvas-set-layer")
    result = ok(run(canvas.set_layer(fresh, "body")))
    assert "Active layer set to 'body'" in result


def test_set_layer_create_if_missing() -> None:
    fresh = _fresh_sprite("canvas-set-layer-create")
    result = ok(run(canvas.set_layer(fresh, "brand-new", create_if_missing=True)))
    assert "Active layer set to 'brand-new'" in result


def test_set_layer_missing_without_create_flag() -> None:
    # Note: the Lua `return` inside `app.transaction(function() ... end)`
    # only exits the transaction closure, not the whole script, so this
    # still falls through to `spr:saveAs` + "OK" and reports success even
    # though no layer was actually activated. Suspected bug in canvas.py's
    # set_layer (the "return" at line ~257 does not skip the trailing
    # print("OK")). Documented here rather than fixed, per task scope.
    fresh = _fresh_sprite("canvas-set-layer-missing")
    result = run(canvas.set_layer(fresh, "no-such-layer", create_if_missing=False))
    assert "Active layer set to 'no-such-layer'" in result


# --- mocked execute_lua_script_checked: process-level subprocess failures ---


def test_create_canvas_reports_subprocess_failure() -> None:
    with patch(_MOCK_PATH) as m:
        m.return_value = (False, "boom")
        result = run(canvas.create_canvas(8, 8, f"{BASE}/create_fail.aseprite"))
    assert result == "Failed to create canvas: boom"


def test_add_frame_reports_subprocess_failure() -> None:
    fresh = _fresh_sprite("canvas-add-frame-fail")
    with patch(_MOCK_PATH) as m:
        m.return_value = (False, "boom")
        result = run(canvas.add_frame(fresh))
    assert result == "Failed to add frame: boom"


def test_set_layer_reports_subprocess_failure() -> None:
    fresh = _fresh_sprite("canvas-set-layer-fail")
    with patch(_MOCK_PATH) as m:
        m.return_value = (False, "boom")
        result = run(canvas.set_layer(fresh, "body"))
    assert result == "Failed to set layer: boom"
