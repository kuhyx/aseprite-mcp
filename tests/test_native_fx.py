"""Native Aseprite command wrappers (native_fx.py)."""

import json
from unittest.mock import patch

from conftest import ok, run

from aseprite_mcp.tools import native_fx, pixel_read


def _hex(pixel_result: str) -> str:
    """Extract the leading '#rrggbb' from get_pixel_color's output."""
    return str(pixel_result).split()[0].lower()


def test_list_convolution_matrices():
    names = json.loads(run(native_fx.list_convolution_matrices()))
    assert "blur-3x3" in names
    assert "sharpen-3x3" in names
    assert "misc-emboss" in names


def test_apply_convolution_rejects_unknown_matrix(sprite):
    res = run(native_fx.apply_convolution(sprite, "not-a-matrix", "body", 1))
    assert res.startswith("Unknown matrix")


def test_outline_native_inside_colours_the_edge(sprite):
    # 'body' has a red rect at (8,8)-(23,23). An inside outline recolours the
    # outer ring, so the left edge at (8, 12) becomes the outline colour.
    ok(run(native_fx.outline_native(sprite, "body", 1, "#00FF00", "inside", "circle")))
    edge = run(pixel_read.get_pixel_color(sprite, 8, 12, "body", 1))
    assert _hex(edge).startswith("#00ff00"), edge


def test_invert_colors_is_exact(sprite):
    before = run(pixel_read.get_pixel_color(sprite, 12, 12, "body", 1))
    r, g, b = (
        int(before.split("r=")[1].split(",")[0]),
        int(before.split("g=")[1].split(",")[0]),
        int(before.split("b=")[1].split(",")[0]),
    )
    ok(run(native_fx.invert_colors(sprite, "body", 1)))
    after = run(pixel_read.get_pixel_color(sprite, 12, 12, "body", 1))
    expected = f"#{255 - r:02x}{255 - g:02x}{255 - b:02x}"
    assert _hex(after).startswith(expected), (before, after, expected)


def test_adjust_hsl_native(sprite):
    ok(run(native_fx.adjust_hsl_native(sprite, "body", 1, 40, 0, 0)))


def test_adjust_brightness_contrast(sprite):
    ok(run(native_fx.adjust_brightness_contrast(sprite, "body", 1, 30, 10)))


def test_apply_convolution_blur(sprite):
    ok(run(native_fx.apply_convolution(sprite, "blur-3x3", "body", 1)))


def test_adjust_hsl_native_rejects_out_of_range(sprite):
    assert run(native_fx.adjust_hsl_native(sprite, "body", 1, 999)).startswith(
        "hue must be"
    )


def test_extract_palette(sprite):
    result = json.loads(ok(run(native_fx.extract_palette(sprite, 16))))
    assert result["count"] >= 1
    assert all(c.startswith("#") and len(c) == 7 for c in result["colors"])


# ── file-not-found guards ───────────────────────────────────────────────

MISSING = "/tmp/ase-pytest/does-not-exist.aseprite"


def test_outline_native_missing_file():
    result = run(native_fx.outline_native(MISSING))
    assert result == f"File {MISSING} not found"


def test_adjust_hsl_native_missing_file():
    result = run(native_fx.adjust_hsl_native(MISSING))
    assert result == f"File {MISSING} not found"


def test_adjust_brightness_contrast_missing_file():
    result = run(native_fx.adjust_brightness_contrast(MISSING))
    assert result == f"File {MISSING} not found"


def test_invert_colors_missing_file():
    result = run(native_fx.invert_colors(MISSING))
    assert result == f"File {MISSING} not found"


def test_apply_convolution_missing_file():
    result = run(native_fx.apply_convolution(MISSING, "blur-3x3"))
    assert result == f"File {MISSING} not found"


def test_extract_palette_missing_file():
    result = run(native_fx.extract_palette(MISSING))
    assert result == f"File {MISSING} not found"


# ── validation branches ─────────────────────────────────────────────────


def test_outline_native_rejects_invalid_color(sprite):
    result = run(native_fx.outline_native(sprite, "body", 1, "not-a-color"))
    assert result == "Invalid color (expected #RRGGBB)"


def test_outline_native_rejects_invalid_place(sprite):
    result = run(native_fx.outline_native(sprite, "body", 1, "#000000", "sideways"))
    assert result == "place must be 'outside' or 'inside'"


def test_outline_native_rejects_invalid_matrix(sprite):
    result = run(
        native_fx.outline_native(sprite, "body", 1, "#000000", "outside", "hexagon")
    )
    assert result == "matrix must be 'circle' or 'square'"


def test_adjust_hsl_native_rejects_saturation_out_of_range(sprite):
    result = run(native_fx.adjust_hsl_native(sprite, "body", 1, 0, 999, 0))
    assert result == "saturation and lightness must be -100..100"


def test_adjust_hsl_native_rejects_lightness_out_of_range(sprite):
    result = run(native_fx.adjust_hsl_native(sprite, "body", 1, 0, 0, 999))
    assert result == "saturation and lightness must be -100..100"


def test_adjust_brightness_contrast_rejects_out_of_range(sprite):
    result = run(native_fx.adjust_brightness_contrast(sprite, "body", 1, 999, 0))
    assert result == "brightness and contrast must be -100..100"
    result = run(native_fx.adjust_brightness_contrast(sprite, "body", 1, 0, 999))
    assert result == "brightness and contrast must be -100..100"


def test_extract_palette_rejects_max_colors_out_of_range(sprite):
    result = run(native_fx.extract_palette(sprite, 0))
    assert result == "max_colors must be 1..256"
    result = run(native_fx.extract_palette(sprite, 257))
    assert result == "max_colors must be 1..256"


# ── "Failed to X" script-error branches (bad layer name) ────────────────


def test_outline_native_reports_layer_not_found(sprite):
    result = run(native_fx.outline_native(sprite, "no-such-layer"))
    assert result.startswith("Failed to outline:")


def test_adjust_hsl_native_reports_layer_not_found(sprite):
    result = run(native_fx.adjust_hsl_native(sprite, "no-such-layer"))
    assert result.startswith("Failed to adjust HSL:")


def test_adjust_brightness_contrast_reports_layer_not_found(sprite):
    result = run(native_fx.adjust_brightness_contrast(sprite, "no-such-layer"))
    assert result.startswith("Failed to adjust brightness/contrast:")


def test_invert_colors_reports_layer_not_found(sprite):
    result = run(native_fx.invert_colors(sprite, "no-such-layer"))
    assert result.startswith("Failed to invert:")


def test_apply_convolution_reports_layer_not_found(sprite):
    result = run(native_fx.apply_convolution(sprite, "blur-3x3", "no-such-layer"))
    assert result.startswith("Failed to apply convolution:")


# ── scoped-region variants (x/y/width/height > 0) ────────────────────────


def test_adjust_hsl_native_with_region(sprite):
    ok(run(native_fx.adjust_hsl_native(sprite, "body", 1, 20, 0, 0, 8, 8, 8, 8)))


def test_adjust_brightness_contrast_with_region(sprite):
    ok(run(native_fx.adjust_brightness_contrast(sprite, "body", 1, 10, 5, 8, 8, 8, 8)))


def test_invert_colors_with_region(sprite):
    ok(run(native_fx.invert_colors(sprite, "body", 1, 8, 8, 8, 8)))


def test_apply_convolution_with_region(sprite):
    ok(run(native_fx.apply_convolution(sprite, "blur-3x3", "body", 1, 8, 8, 8, 8)))


def test_extract_palette_with_alpha(sprite):
    result = json.loads(ok(run(native_fx.extract_palette(sprite, 8, with_alpha=True))))
    assert result["count"] >= 1


def test_extract_palette_reports_subprocess_failure(sprite):
    with patch(
        "aseprite_mcp.tools.native_fx.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(native_fx.extract_palette(sprite))
    assert result == "Failed to extract palette: boom"
