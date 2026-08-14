"""Region operation tools (selection.py)."""

from unittest.mock import patch

from conftest import ok, run

from aseprite_mcp.tools import canvas, selection


def test_copy_region(sprite: str) -> None:
    ok(run(selection.copy_region(sprite, "body", 1, 8, 8, 8, 8, 20, 20)))


def test_move_region(sprite: str) -> None:
    ok(run(selection.move_region(sprite, "body", 1, 20, 20, 8, 8, 0, 0)))


def test_erase_region(sprite: str) -> None:
    ok(run(selection.erase_region(sprite, "body", 1, 0, 0, 4, 4)))


def test_erase_color(sprite: str) -> None:
    result = ok(run(selection.erase_color(sprite, "body", 1, "#D04648", 0)))
    assert "Erased" in result


# ── file-not-found guards ───────────────────────────────────────────────

MISSING = "/tmp/ase-pytest/does-not-exist.aseprite"


def test_move_region_missing_file() -> None:
    result = run(selection.move_region(MISSING, "body", 1, 0, 0, 4, 4, 0, 0))
    assert result == f"File {MISSING} not found"


def test_copy_region_missing_file() -> None:
    result = run(selection.copy_region(MISSING, "body", 1, 0, 0, 4, 4, 0, 0))
    assert result == f"File {MISSING} not found"


def test_erase_region_missing_file() -> None:
    result = run(selection.erase_region(MISSING, "body", 1, 0, 0, 4, 4))
    assert result == f"File {MISSING} not found"


def test_erase_color_missing_file() -> None:
    result = run(selection.erase_color(MISSING, "body", 1, "#FF0000"))
    assert result == f"File {MISSING} not found"


# ── validation branches ─────────────────────────────────────────────────


def test_move_region_rejects_non_positive_width(sprite: str) -> None:
    result = run(selection.move_region(sprite, "body", 1, 0, 0, 0, 4, 0, 0))
    assert result == "Width and height must be > 0"


def test_move_region_rejects_non_positive_height(sprite: str) -> None:
    result = run(selection.move_region(sprite, "body", 1, 0, 0, 4, 0, 0, 0))
    assert result == "Width and height must be > 0"


def test_copy_region_rejects_non_positive_dimensions(sprite: str) -> None:
    result = run(selection.copy_region(sprite, "body", 1, 0, 0, 0, 0, 0, 0))
    assert result == "Width and height must be > 0"


def test_erase_region_rejects_non_positive_dimensions(sprite: str) -> None:
    result = run(selection.erase_region(sprite, "body", 1, 0, 0, -1, 4))
    assert result == "Width and height must be > 0"


def test_erase_color_rejects_invalid_color(sprite: str) -> None:
    result = run(selection.erase_color(sprite, "body", 1, "not-a-color"))
    assert result == "Invalid color value: not-a-color"


def test_erase_color_rejects_tolerance_out_of_range(sprite: str) -> None:
    result = run(selection.erase_color(sprite, "body", 1, "#FF0000", 256))
    assert result == "Tolerance must be between 0 and 255"
    result = run(selection.erase_color(sprite, "body", 1, "#FF0000", -1))
    assert result == "Tolerance must be between 0 and 255"


# ── "Failed to X" script-error branches ─────────────────────────────────


def test_move_region_reports_layer_not_found(sprite: str) -> None:
    result = run(selection.move_region(sprite, "no-such-layer", 1, 0, 0, 4, 4, 0, 0))
    assert result.startswith("Failed to move region:")


def test_move_region_reports_frame_out_of_range(sprite: str) -> None:
    result = run(selection.move_region(sprite, "body", 99, 0, 0, 4, 4, 0, 0))
    assert result.startswith("Failed to move region:")
    assert "out of range" in result


def test_copy_region_reports_source_layer_not_found(sprite: str) -> None:
    result = run(selection.copy_region(sprite, "no-such-layer", 1, 0, 0, 4, 4, 0, 0))
    assert result.startswith("Failed to copy region:")


def test_copy_region_reports_target_layer_not_found(sprite: str) -> None:
    result = run(
        selection.copy_region(
            sprite, "body", 1, 0, 0, 4, 4, 0, 0, target_layer_name="no-such-layer"
        )
    )
    assert result.startswith("Failed to copy region:")


def test_copy_region_reports_source_frame_out_of_range(sprite: str) -> None:
    result = run(selection.copy_region(sprite, "body", 99, 0, 0, 4, 4, 0, 0))
    assert result.startswith("Failed to copy region:")
    assert "Source frame index out of range" in result


def test_copy_region_reports_target_frame_out_of_range(sprite: str) -> None:
    result = run(
        selection.copy_region(
            sprite, "body", 1, 0, 0, 4, 4, 0, 0, target_frame_index=99
        )
    )
    assert result.startswith("Failed to copy region:")
    assert "Target frame index out of range" in result


def test_copy_region_to_explicit_target_layer_and_frame(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "copy-target")))
    ok(run(canvas.add_frame(sprite)))
    result = ok(
        run(
            selection.copy_region(
                sprite,
                "body",
                1,
                8,
                8,
                4,
                4,
                0,
                0,
                target_layer_name="copy-target",
                target_frame_index=2,
            )
        )
    )
    assert "Copied" in result


def test_erase_region_reports_layer_not_found(sprite: str) -> None:
    result = run(selection.erase_region(sprite, "no-such-layer", 1, 0, 0, 4, 4))
    assert result.startswith("Failed to erase region:")


def test_erase_region_reports_frame_out_of_range(sprite: str) -> None:
    result = run(selection.erase_region(sprite, "body", 99, 0, 0, 4, 4))
    assert result.startswith("Failed to erase region:")
    assert "out of range" in result


def test_erase_color_reports_layer_not_found(sprite: str) -> None:
    result = run(selection.erase_color(sprite, "no-such-layer", 1, "#FF0000"))
    assert result.startswith("Failed to erase color:")


def test_erase_color_reports_frame_out_of_range(sprite: str) -> None:
    result = run(selection.erase_color(sprite, "body", 99, "#FF0000"))
    assert result.startswith("Failed to erase color:")
    assert "out of range" in result


def test_erase_color_with_no_matching_pixels_reports_zero(sprite: str) -> None:
    result = ok(run(selection.erase_color(sprite, "body", 1, "#123456", 0)))
    assert "Erased 0 pixels" in result


def test_erase_color_skips_non_count_lines_before_matching(sprite: str) -> None:
    # Forces the `for line in output.splitlines()` loop to iterate past at
    # least one non-"COUNT:" line before finding the real one, exercising
    # the loop-continues branch (as opposed to matching on the first line).
    with patch(
        "aseprite_mcp.tools.selection.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "some other output\nCOUNT:7")
        result = run(selection.erase_color(sprite, "body", 1, "#FF0000", 0))
    assert "Erased 7 pixels" in result
