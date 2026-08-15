"""Coverage-focused tests for drawing.py.

Targets the layer-less tools (draw_pixels, draw_line, draw_rectangle,
fill_area, draw_circle) which had zero coverage, the still-dark branches
of the "_at" tools (draw_circle_at, fill_area_at, draw_path,
draw_polygon, apply_gradient_rect), every "file not found" / validation
early-return, and the "ERROR:"-from-Lua failure paths (bad layer name /
out-of-range frame index), which do reach the `success=False` branch per
AsepriteCommand.execute_lua_script_checked (an "ERROR:" line flips
success even though the subprocess itself exits 0).

The five layer-less tools (draw_pixels, draw_line, draw_rectangle,
fill_area, draw_circle) target app.activeCel / spr.layers[1] rather than
a named layer. They all grow the cel now: draw_pixels and draw_line gained
the union/regrow block in 4119aff, and the other three dispatch
app.useTool, which grows the cel itself. So for those five we still only
assert success (`ok(...)`), never pixel content -- there is no reliable
way to know which cel is active from here, and asserting content would be
testing a guess. Cel growth for the layer-less tools is asserted in
test_drawing_fixes.py, where the target layer is unambiguous.
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from conftest import ok, run

from aseprite_mcp.tools import canvas, drawing, pixel_read
from aseprite_mcp.tools.drawing import _parse_write_counts


def _rgba(pixel_result: str) -> tuple[int, int, int, int]:
    s = str(pixel_result)
    return (
        int(s.split("r=")[1].split(",", maxsplit=1)[0]),
        int(s.split("g=")[1].split(",", maxsplit=1)[0]),
        int(s.split("b=")[1].split(",", maxsplit=1)[0]),
        int(s.split("a=")[1].split(")", maxsplit=1)[0]),
    )


# ---------------------------------------------------------------------------
# _parse_write_counts helper -- exercised directly, no Aseprite needed.
# ---------------------------------------------------------------------------


def test_parse_write_counts_finds_marker_after_noise() -> None:
    # Marker not on the first line: the loop must skip leading noise.
    assert _parse_write_counts("some noise\nOK:3:1", 4) == (3, 1)


def test_parse_write_counts_too_few_parts_falls_through() -> None:
    # "OK:3" has only 2 parts after split(":"); falls through to the
    # total/0 fallback at the end of the function.
    assert _parse_write_counts("OK:3", 4) == (4, 0)


def test_parse_write_counts_non_numeric_breaks() -> None:
    # Non-numeric fields raise ValueError inside the try, hit `break`,
    # and fall through to the total/0 fallback.
    assert _parse_write_counts("OK:a:b", 4) == (4, 0)


def test_parse_write_counts_no_marker_at_all() -> None:
    assert _parse_write_counts("", 5) == (5, 0)
    assert _parse_write_counts("random output with no marker", 5) == (5, 0)


# ---------------------------------------------------------------------------
# Layer-less tools: draw_pixels, draw_line, draw_rectangle, fill_area,
# draw_circle. Success-path + file-not-found + validation only.
# ---------------------------------------------------------------------------


def test_draw_pixels_success(sprite: str) -> None:
    ok(run(drawing.draw_pixels(sprite, [{"x": 10, "y": 10, "color": "#123456"}])))


def test_draw_pixels_file_not_found() -> None:
    result = run(
        drawing.draw_pixels(
            "/tmp/ase-pytest/does-not-exist.aseprite",
            [{"x": 0, "y": 0, "color": "#000000"}],
        )
    )
    assert "not found" in result


def test_draw_pixels_invalid_color(sprite: str) -> None:
    result = run(drawing.draw_pixels(sprite, [{"x": 0, "y": 0, "color": "#ZZZZZZ"}]))
    assert "Invalid color value" in result


def test_draw_line_success(sprite: str) -> None:
    ok(run(drawing.draw_line(sprite, 2, 2, 10, 10, "#654321", 2)))


def test_draw_line_file_not_found() -> None:
    result = run(
        drawing.draw_line("/tmp/ase-pytest/does-not-exist.aseprite", 0, 0, 5, 5)
    )
    assert "not found" in result


def test_draw_line_invalid_color(sprite: str) -> None:
    result = run(drawing.draw_line(sprite, 0, 0, 5, 5, "#GGG"))
    assert "Invalid color value" in result


def test_draw_rectangle_success(sprite: str) -> None:
    ok(run(drawing.draw_rectangle(sprite, 1, 1, 5, 5, "#ABCDEF", fill=False)))


def test_draw_rectangle_filled(sprite: str) -> None:
    ok(run(drawing.draw_rectangle(sprite, 1, 1, 5, 5, "#ABCDEF", fill=True)))


def test_draw_rectangle_file_not_found() -> None:
    result = run(
        drawing.draw_rectangle("/tmp/ase-pytest/does-not-exist.aseprite", 0, 0, 5, 5)
    )
    assert "not found" in result


def test_draw_rectangle_rejects_zero_width(sprite: str) -> None:
    result = run(drawing.draw_rectangle(sprite, 0, 0, 0, 5))
    assert "must be > 0" in result


def test_draw_rectangle_rejects_zero_height(sprite: str) -> None:
    result = run(drawing.draw_rectangle(sprite, 0, 0, 5, 0))
    assert "must be > 0" in result


def test_draw_rectangle_invalid_color(sprite: str) -> None:
    result = run(drawing.draw_rectangle(sprite, 0, 0, 5, 5, "#NOTHEX"))
    assert "Invalid color value" in result


def test_fill_area_success(sprite: str) -> None:
    ok(run(drawing.fill_area(sprite, 1, 1, "#112233")))


def test_fill_area_file_not_found() -> None:
    result = run(drawing.fill_area("/tmp/ase-pytest/does-not-exist.aseprite", 0, 0))
    assert "not found" in result


def test_fill_area_invalid_color(sprite: str) -> None:
    result = run(drawing.fill_area(sprite, 0, 0, "#XYZXYZ"))
    assert "Invalid color value" in result


def test_draw_circle_outline_success(sprite: str) -> None:
    ok(run(drawing.draw_circle(sprite, 16, 16, 3, "#445566", fill=False)))


def test_draw_circle_filled_success(sprite: str) -> None:
    ok(run(drawing.draw_circle(sprite, 16, 16, 3, "#445566", fill=True)))


def test_draw_circle_file_not_found() -> None:
    result = run(
        drawing.draw_circle("/tmp/ase-pytest/does-not-exist.aseprite", 16, 16, 3)
    )
    assert "not found" in result


def test_draw_circle_invalid_color(sprite: str) -> None:
    result = run(drawing.draw_circle(sprite, 16, 16, 3, "#BADCOL"))
    assert "Invalid color value" in result


# ---------------------------------------------------------------------------
# draw_pixels_at: file-not-found only (success path already covered
# elsewhere in test_drawing_fixes.py).
# ---------------------------------------------------------------------------


def test_draw_pixels_at_file_not_found() -> None:
    result = run(
        drawing.draw_pixels_at(
            "/tmp/ase-pytest/does-not-exist.aseprite",
            "body",
            1,
            [{"x": 0, "y": 0, "color": "#000000"}],
        )
    )
    assert "not found" in result


# ---------------------------------------------------------------------------
# draw_line_at: file-not-found, invalid color, bad layer, bad frame.
# ---------------------------------------------------------------------------


def test_draw_line_at_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "line_at")))
    ok(
        run(
            drawing.draw_line_at(
                sprite, "line_at", 1, 2, 2, 10, 10, "#123123", 1, create_if_missing=True
            )
        )
    )


def test_draw_line_at_file_not_found() -> None:
    result = run(
        drawing.draw_line_at(
            "/tmp/ase-pytest/does-not-exist.aseprite", "body", 1, 0, 0, 5, 5
        )
    )
    assert "not found" in result


def test_draw_line_at_invalid_color(sprite: str) -> None:
    result = run(drawing.draw_line_at(sprite, "body", 1, 0, 0, 5, 5, "#GGGGGG"))
    assert "Invalid color value" in result


def test_draw_line_at_bad_layer(sprite: str) -> None:
    result = run(drawing.draw_line_at(sprite, "no-such-layer", 1, 0, 0, 5, 5))
    assert "Failed to draw line" in result


def test_draw_line_at_bad_frame(sprite: str) -> None:
    result = run(drawing.draw_line_at(sprite, "body", 99, 0, 0, 5, 5))
    assert "Failed to draw line" in result


# ---------------------------------------------------------------------------
# draw_rectangle_at: success, validation, file-not-found, bad layer/frame.
# ---------------------------------------------------------------------------


def test_draw_rectangle_at_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "rect_at")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite,
                "rect_at",
                1,
                2,
                2,
                5,
                5,
                "#654654",
                fill=False,
                create_if_missing=True,
            )
        )
    )


def test_draw_rectangle_at_file_not_found() -> None:
    result = run(
        drawing.draw_rectangle_at(
            "/tmp/ase-pytest/does-not-exist.aseprite", "body", 1, 0, 0, 5, 5
        )
    )
    assert "not found" in result


def test_draw_rectangle_at_rejects_zero_size(sprite: str) -> None:
    result = run(drawing.draw_rectangle_at(sprite, "body", 1, 0, 0, 0, 5))
    assert "must be > 0" in result


def test_draw_rectangle_at_invalid_color(sprite: str) -> None:
    result = run(drawing.draw_rectangle_at(sprite, "body", 1, 0, 0, 5, 5, "#ZZZ123"))
    assert "Invalid color value" in result


def test_draw_rectangle_at_bad_layer(sprite: str) -> None:
    result = run(drawing.draw_rectangle_at(sprite, "no-such-layer", 1, 0, 0, 5, 5))
    assert "Failed to draw rectangle" in result


def test_draw_rectangle_at_bad_frame(sprite: str) -> None:
    result = run(drawing.draw_rectangle_at(sprite, "body", 99, 0, 0, 5, 5))
    assert "Failed to draw rectangle" in result


# ---------------------------------------------------------------------------
# draw_circle_at: outline + filled, file-not-found, invalid color, bad
# layer/frame. Previously zero coverage (722-771).
# ---------------------------------------------------------------------------


def test_draw_circle_at_outline_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "circle_at")))
    ok(
        run(
            drawing.draw_circle_at(
                sprite,
                "circle_at",
                1,
                16,
                16,
                4,
                "#0000FF",
                fill=False,
                create_if_missing=True,
            )
        )
    )
    r, g, b, _ = _rgba(run(pixel_read.get_pixel_color(sprite, 16, 12, "circle_at", 1)))
    assert (r, g, b) == (0, 0, 255)


def test_draw_circle_at_filled_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "circle_at_fill")))
    ok(
        run(
            drawing.draw_circle_at(
                sprite,
                "circle_at_fill",
                1,
                16,
                16,
                4,
                "#00FF00",
                fill=True,
                create_if_missing=True,
            )
        )
    )
    r, g, b, _ = _rgba(
        run(pixel_read.get_pixel_color(sprite, 16, 16, "circle_at_fill", 1))
    )
    assert (r, g, b) == (0, 255, 0)


def test_draw_circle_at_file_not_found() -> None:
    result = run(
        drawing.draw_circle_at(
            "/tmp/ase-pytest/does-not-exist.aseprite", "body", 1, 16, 16, 4
        )
    )
    assert "not found" in result


def test_draw_circle_at_invalid_color(sprite: str) -> None:
    result = run(drawing.draw_circle_at(sprite, "body", 1, 16, 16, 4, "#NOPE12"))
    assert "Invalid color value" in result


def test_draw_circle_at_bad_layer(sprite: str) -> None:
    result = run(drawing.draw_circle_at(sprite, "no-such-layer", 1, 16, 16, 4))
    assert "Failed to draw circle" in result


def test_draw_circle_at_bad_frame(sprite: str) -> None:
    result = run(drawing.draw_circle_at(sprite, "body", 99, 16, 16, 4))
    assert "Failed to draw circle" in result


# ---------------------------------------------------------------------------
# fill_area_at: success, file-not-found, invalid color, bad layer/frame.
# Previously zero coverage (795-840).
# ---------------------------------------------------------------------------


def test_fill_area_at_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "fill_at")))
    ok(
        run(
            drawing.draw_rectangle_at(
                sprite,
                "fill_at",
                1,
                4,
                4,
                10,
                10,
                "#101010",
                fill=True,
                create_if_missing=True,
            )
        )
    )
    ok(
        run(
            drawing.fill_area_at(
                sprite, "fill_at", 1, 5, 5, "#202020", create_if_missing=True
            )
        )
    )
    r, g, b, _ = _rgba(run(pixel_read.get_pixel_color(sprite, 5, 5, "fill_at", 1)))
    assert (r, g, b) == (0x20, 0x20, 0x20)


def test_fill_area_at_file_not_found() -> None:
    result = run(
        drawing.fill_area_at("/tmp/ase-pytest/does-not-exist.aseprite", "body", 1, 0, 0)
    )
    assert "not found" in result


def test_fill_area_at_invalid_color(sprite: str) -> None:
    result = run(drawing.fill_area_at(sprite, "body", 1, 0, 0, "#BADCOL"))
    assert "Invalid color value" in result


def test_fill_area_at_bad_layer(sprite: str) -> None:
    result = run(drawing.fill_area_at(sprite, "no-such-layer", 1, 0, 0))
    assert "Failed to fill area" in result


def test_fill_area_at_bad_frame(sprite: str) -> None:
    result = run(drawing.fill_area_at(sprite, "body", 99, 0, 0))
    assert "Failed to fill area" in result


# ---------------------------------------------------------------------------
# draw_polygon: outline + filled, degenerate (<3 points), file-not-found,
# invalid color, bad layer/frame.
# ---------------------------------------------------------------------------


def test_draw_polygon_outline_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "poly_outline")))
    pts = [{"x": 4, "y": 4}, {"x": 12, "y": 4}, {"x": 8, "y": 12}]
    ok(
        run(
            drawing.draw_polygon(
                sprite,
                "poly_outline",
                1,
                pts,
                "#EEEEEE",
                fill=False,
                create_if_missing=True,
            )
        )
    )


def test_draw_polygon_filled_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "poly_fill")))
    pts = [{"x": 4, "y": 4}, {"x": 12, "y": 4}, {"x": 12, "y": 12}, {"x": 4, "y": 12}]
    ok(
        run(
            drawing.draw_polygon(
                sprite,
                "poly_fill",
                1,
                pts,
                "#FF00FF",
                fill=True,
                create_if_missing=True,
            )
        )
    )
    r, g, b, _ = _rgba(run(pixel_read.get_pixel_color(sprite, 8, 8, "poly_fill", 1)))
    assert (r, g, b) == (255, 0, 255)


def test_draw_polygon_file_not_found() -> None:
    result = run(
        drawing.draw_polygon(
            "/tmp/ase-pytest/does-not-exist.aseprite",
            "body",
            1,
            [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}],
        )
    )
    assert "not found" in result


def test_draw_polygon_rejects_too_few_points(sprite: str) -> None:
    result = run(
        drawing.draw_polygon(sprite, "body", 1, [{"x": 0, "y": 0}, {"x": 1, "y": 1}])
    )
    assert "at least 3 points" in result


def test_draw_polygon_invalid_color(sprite: str) -> None:
    pts = [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}]
    result = run(drawing.draw_polygon(sprite, "body", 1, pts, "#GARBAG"))
    assert "Invalid color value" in result


def test_draw_polygon_bad_layer(sprite: str) -> None:
    pts = [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}]
    result = run(drawing.draw_polygon(sprite, "no-such-layer", 1, pts))
    assert "Failed to draw polygon" in result


def test_draw_polygon_bad_frame(sprite: str) -> None:
    pts = [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}]
    result = run(drawing.draw_polygon(sprite, "body", 99, pts))
    assert "Failed to draw polygon" in result


# ---------------------------------------------------------------------------
# draw_path: success, thickness>1, degenerate (<2 points), file-not-found,
# invalid color, bad layer/frame. Previously zero coverage (989-1063).
# ---------------------------------------------------------------------------


def test_draw_path_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "path_thin")))
    pts = [{"x": 2, "y": 2}, {"x": 10, "y": 2}, {"x": 10, "y": 10}]
    ok(
        run(
            drawing.draw_path(
                sprite, "path_thin", 1, pts, "#123ABC", 1, create_if_missing=True
            )
        )
    )
    r, g, b, _ = _rgba(run(pixel_read.get_pixel_color(sprite, 6, 2, "path_thin", 1)))
    assert (r, g, b) == (0x12, 0x3A, 0xBC)


def test_draw_path_thick_success(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "path_thick")))
    pts = [{"x": 2, "y": 2}, {"x": 10, "y": 2}]
    ok(
        run(
            drawing.draw_path(
                sprite, "path_thick", 1, pts, "#654321", 3, create_if_missing=True
            )
        )
    )


def test_draw_path_file_not_found() -> None:
    result = run(
        drawing.draw_path(
            "/tmp/ase-pytest/does-not-exist.aseprite",
            "body",
            1,
            [{"x": 0, "y": 0}, {"x": 1, "y": 1}],
        )
    )
    assert "not found" in result


def test_draw_path_rejects_too_few_points(sprite: str) -> None:
    result = run(drawing.draw_path(sprite, "body", 1, [{"x": 0, "y": 0}]))
    assert "at least 2 points" in result


def test_draw_path_invalid_color(sprite: str) -> None:
    result = run(
        drawing.draw_path(
            sprite, "body", 1, [{"x": 0, "y": 0}, {"x": 1, "y": 1}], "#NOTAHEX"
        )
    )
    assert "Invalid color value" in result


def test_draw_path_bad_layer(sprite: str) -> None:
    result = run(
        drawing.draw_path(
            sprite, "no-such-layer", 1, [{"x": 0, "y": 0}, {"x": 1, "y": 1}]
        )
    )
    assert "Failed to draw path" in result


def test_draw_path_bad_frame(sprite: str) -> None:
    result = run(
        drawing.draw_path(sprite, "body", 99, [{"x": 0, "y": 0}, {"x": 1, "y": 1}])
    )
    assert "Failed to draw path" in result


# ---------------------------------------------------------------------------
# apply_gradient_rect: horizontal (already covered elsewhere) + vertical,
# validation, file-not-found, bad layer/frame.
# ---------------------------------------------------------------------------


def test_apply_gradient_rect_vertical(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "grad_vert")))
    ok(
        run(
            drawing.apply_gradient_rect(
                sprite,
                "grad_vert",
                1,
                4,
                4,
                1,
                16,
                "#000000",
                "#FFFFFF",
                horizontal=False,
                create_if_missing=True,
            )
        )
    )
    top = _rgba(run(pixel_read.get_pixel_color(sprite, 4, 4, "grad_vert", 1)))
    bottom = _rgba(run(pixel_read.get_pixel_color(sprite, 4, 19, "grad_vert", 1)))
    assert top[0] < bottom[0], (top, bottom)  # dark -> light, top to bottom


def test_apply_gradient_rect_file_not_found() -> None:
    result = run(
        drawing.apply_gradient_rect(
            "/tmp/ase-pytest/does-not-exist.aseprite",
            "body",
            1,
            0,
            0,
            5,
            5,
            "#000000",
            "#FFFFFF",
        )
    )
    assert "not found" in result


def test_apply_gradient_rect_rejects_zero_size(sprite: str) -> None:
    result = run(
        drawing.apply_gradient_rect(sprite, "body", 1, 0, 0, 0, 5, "#000000", "#FFFFFF")
    )
    assert "must be > 0" in result


def test_apply_gradient_rect_invalid_start_color(sprite: str) -> None:
    result = run(
        drawing.apply_gradient_rect(
            sprite, "body", 1, 0, 0, 5, 5, "#BADSTRT", "#FFFFFF"
        )
    )
    assert "Invalid color_start value" in result


def test_apply_gradient_rect_invalid_end_color(sprite: str) -> None:
    result = run(
        drawing.apply_gradient_rect(
            sprite, "body", 1, 0, 0, 5, 5, "#000000", "#BADEND1"
        )
    )
    assert "Invalid color_end value" in result


def test_apply_gradient_rect_bad_layer(sprite: str) -> None:
    result = run(
        drawing.apply_gradient_rect(
            sprite, "no-such-layer", 1, 0, 0, 5, 5, "#000000", "#FFFFFF"
        )
    )
    assert "Failed to apply gradient" in result


def test_apply_gradient_rect_bad_frame(sprite: str) -> None:
    result = run(
        drawing.apply_gradient_rect(
            sprite, "body", 99, 0, 0, 5, 5, "#000000", "#FFFFFF"
        )
    )
    assert "Failed to apply gradient" in result


# ---------------------------------------------------------------------------
# draw_ellipse_at: fill=False branch (test_drawing.py only covers
# fill=True), file-not-found, degenerate radii, invalid color, bad
# layer/frame.
# ---------------------------------------------------------------------------


def test_draw_ellipse_at_outline(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "ellipse_outline")))
    ok(
        run(
            drawing.draw_ellipse_at(
                sprite, "ellipse_outline", 1, 16, 16, 6, 4, "#306230", fill=False
            )
        )
    )


def test_draw_ellipse_at_file_not_found() -> None:
    result = run(
        drawing.draw_ellipse_at(
            "/tmp/ase-pytest/does-not-exist.aseprite", "body", 1, 16, 16, 6, 4
        )
    )
    assert "not found" in result


def test_draw_ellipse_at_rejects_zero_radius_y(sprite: str) -> None:
    result = run(drawing.draw_ellipse_at(sprite, "body", 1, 16, 16, 6, 0))
    assert "must be > 0" in result


def test_draw_ellipse_at_invalid_color(sprite: str) -> None:
    result = run(drawing.draw_ellipse_at(sprite, "body", 1, 16, 16, 6, 4, "#NOTHEX1"))
    assert "Invalid color value" in result


def test_draw_ellipse_at_bad_layer(sprite: str) -> None:
    result = run(drawing.draw_ellipse_at(sprite, "no-such-layer", 1, 16, 16, 6, 4))
    assert "Failed to draw ellipse" in result


def test_draw_ellipse_at_bad_frame(sprite: str) -> None:
    result = run(drawing.draw_ellipse_at(sprite, "body", 99, 16, 16, 6, 4))
    assert "Failed to draw ellipse" in result


# --- mocked execute_lua_script_checked: process-level subprocess failures ---
# The five layer-less tools have no layer_name param, so "bad layer"/"bad
# frame" can't reach their failure branch - only a real subprocess failure
# (mocked here) or a genuine ERROR: line from the script itself can.


def test_draw_pixels_reports_subprocess_failure() -> None:
    with patch(
        "aseprite_mcp.tools.drawing.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(
            drawing.draw_pixels(
                "/tmp/ase-pytest/does-not-exist.aseprite", [{"x": 0, "y": 0}]
            )
        )
    assert "not found" in result


def test_draw_pixels_reports_subprocess_failure_on_real_file(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.drawing.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(
            drawing.draw_pixels(sprite, [{"x": 0, "y": 0, "color": "#FF0000"}])
        )
    assert result == "Failed to draw pixels: boom"


def test_draw_line_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.drawing.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(drawing.draw_line(sprite, 0, 0, 4, 4))
    assert result == "Failed to draw line: boom"


def test_draw_rectangle_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.drawing.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(drawing.draw_rectangle(sprite, 0, 0, 4, 4))
    assert result == "Failed to draw rectangle: boom"


def test_fill_area_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.drawing.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(drawing.fill_area(sprite, 0, 0))
    assert result == "Failed to fill area: boom"


def test_draw_circle_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.drawing.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(drawing.draw_circle(sprite, 8, 8, 4))
    assert result == "Failed to draw circle: boom"


def test_draw_pixels_at_reports_subprocess_failure(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "fail-pixels-at")))
    with patch(
        "aseprite_mcp.tools.drawing.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(
            drawing.draw_pixels_at(
                sprite, "fail-pixels-at", 1, [{"x": 0, "y": 0, "color": "#FF0000"}]
            )
        )
    assert result == "Failed to draw pixels: boom"


def test_draw_pixels_at_empty_pixel_list_uses_fallback_bounds(sprite: str) -> None:
    # xs/ys are both empty when pixels=[], hitting the need_x=need_y=0,
    # need_w=need_h=1 fallback instead of the min/max-derived bounding box.
    ok(run(canvas.add_layer(sprite, "empty-pixels-at")))
    result = ok(run(drawing.draw_pixels_at(sprite, "empty-pixels-at", 1, [])))
    assert result == (
        f"Pixels drawn on 'empty-pixels-at' frame 1 in {sprite} (0 pixels)"
    )


# --- fabricated success: _at tools with create_if_missing=False ---
#
# Every one of these guards a missing cel with a `return` that used to sit
# inside app.transaction, so the script fell through to spr:saveAs +
# print("OK") and the tool reported drawing it never did. The guards are now
# hoisted above the transaction; mtime proves saveAs never runs.


def _no_cel_calls(sprite: str, layer: str) -> list[tuple[str, Callable[[], object]]]:
    """One no-cel call per _at tool, all with create_if_missing=False.

    Each entry is a thunk so the coroutine is only created when it is about
    to be awaited -- building them all up front leaves the later ones
    un-awaited when an earlier assertion fails.
    """
    return [
        (
            "draw_pixels_at",
            lambda: drawing.draw_pixels_at(
                sprite,
                layer,
                1,
                [{"x": 1, "y": 1, "color": "#FF0000"}],
                create_if_missing=False,
            ),
        ),
        (
            "draw_line_at",
            lambda: drawing.draw_line_at(
                sprite, layer, 1, 0, 0, 4, 4, "#FF0000", 1, create_if_missing=False
            ),
        ),
        (
            "draw_rectangle_at",
            lambda: drawing.draw_rectangle_at(
                sprite, layer, 1, 0, 0, 4, 4, "#FF0000", create_if_missing=False
            ),
        ),
        (
            "draw_circle_at",
            lambda: drawing.draw_circle_at(
                sprite, layer, 1, 4, 4, 2, "#FF0000", create_if_missing=False
            ),
        ),
        (
            "fill_area_at",
            lambda: drawing.fill_area_at(
                sprite, layer, 1, 1, 1, "#FF0000", create_if_missing=False
            ),
        ),
        (
            "draw_ellipse_at",
            lambda: drawing.draw_ellipse_at(
                sprite, layer, 1, 4, 4, 3, 2, "#FF0000", create_if_missing=False
            ),
        ),
        (
            "draw_polygon",
            lambda: drawing.draw_polygon(
                sprite,
                layer,
                1,
                [{"x": 0, "y": 0}, {"x": 4, "y": 0}, {"x": 2, "y": 4}],
                "#FF0000",
                create_if_missing=False,
            ),
        ),
        (
            "draw_path",
            lambda: drawing.draw_path(
                sprite,
                layer,
                1,
                [{"x": 0, "y": 0}, {"x": 4, "y": 4}],
                "#FF0000",
                1,
                create_if_missing=False,
            ),
        ),
        (
            "apply_gradient_rect",
            lambda: drawing.apply_gradient_rect(
                sprite,
                layer,
                1,
                0,
                0,
                4,
                4,
                "#000000",
                "#FFFFFF",
                create_if_missing=False,
            ),
        ),
    ]


def test_at_tools_no_cel_without_create_flag_error(sprite: str) -> None:
    layer = "no-cel-at-tools"
    ok(run(canvas.add_layer(sprite, layer)))
    failures: list[str] = []
    for name, make_call in _no_cel_calls(sprite, layer):
        before = Path(sprite).stat().st_mtime_ns
        result = str(run(make_call()))  # type: ignore[arg-type]
        if not result.startswith("Failed"):
            failures.append(f"{name}: fabricated success -> {result}")
        elif Path(sprite).stat().st_mtime_ns != before:
            failures.append(f"{name}: saved the file on the error path")
    assert not failures, "\n".join(failures)


def test_draw_circle_rejects_non_positive_radius(sprite: str) -> None:
    assert run(drawing.draw_circle(sprite, 16, 16, 0)) == "Radius must be > 0"
    assert run(drawing.draw_circle(sprite, 16, 16, -3)) == "Radius must be > 0"


def test_draw_circle_at_rejects_non_positive_radius(sprite: str) -> None:
    assert (
        run(drawing.draw_circle_at(sprite, "body", 1, 8, 8, 0)) == "Radius must be > 0"
    )
    assert (
        run(drawing.draw_circle_at(sprite, "body", 1, 8, 8, -2)) == "Radius must be > 0"
    )
