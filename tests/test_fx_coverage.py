"""Coverage tests for fx.py: validation, error, and branch paths."""

from unittest.mock import patch

from conftest import BASE, ok, run

from aseprite_mcp.tools import canvas, drawing, fx


def _fresh_sprite(name: str) -> str:
    path = f"{BASE}/{name}.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    ok(run(canvas.add_layer(path, "body")))
    ok(
        run(
            drawing.draw_rectangle_at(path, "body", 1, 2, 2, 8, 8, "#D04648", fill=True)
        )
    )
    return path


# ── missing-file guards ──────────────────────────────────────────────────


def test_outline_cel_missing_file() -> None:
    result = run(fx.outline_cel(f"{BASE}/does-not-exist.aseprite", "body", 1))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_replace_color_missing_file() -> None:
    result = run(
        fx.replace_color(
            f"{BASE}/does-not-exist.aseprite", "body", 1, "#000000", "#FFFFFF"
        )
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_adjust_hsl_missing_file() -> None:
    result = run(fx.adjust_hsl(f"{BASE}/does-not-exist.aseprite", "body", 1))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_apply_dither_gradient_missing_file() -> None:
    result = run(
        fx.apply_dither_gradient(
            f"{BASE}/does-not-exist.aseprite",
            "body",
            1,
            0,
            0,
            4,
            4,
            "#000000",
            "#FFFFFF",
        )
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_apply_dither_pattern_missing_file() -> None:
    result = run(
        fx.apply_dither_pattern(
            f"{BASE}/does-not-exist.aseprite",
            "body",
            1,
            0,
            0,
            4,
            4,
            "#000000",
            "#FFFFFF",
        )
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


# ── outline_cel ───────────────────────────────────────────────────────


def test_outline_cel_rejects_bad_color() -> None:
    fresh = _fresh_sprite("fx-outline-badcolor")
    result = run(fx.outline_cel(fresh, "body", 1, color="not-a-color"))
    assert result == "Invalid color value: not-a-color"


def test_outline_cel_reports_frame_out_of_range() -> None:
    fresh = _fresh_sprite("fx-outline-oob")
    result = run(fx.outline_cel(fresh, "body", 999))
    assert result.startswith("Failed to outline cel:")
    assert "out of range" in result


def test_outline_cel_reports_layer_not_found() -> None:
    fresh = _fresh_sprite("fx-outline-nolayer")
    result = run(fx.outline_cel(fresh, "no-such-layer", 1))
    assert result.startswith("Failed to outline cel:")
    assert "Layer not found" in result


def test_outline_cel_reports_no_cel() -> None:
    # outline_cel calls normalize_cel(..., create=false), so a layer with
    # no cel at that frame hits the "No cel at that layer/frame" guard
    # instead of creating one (unlike the dither tools, which default to
    # create_if_missing=True).
    fresh = _fresh_sprite("fx-outline-nocel")
    ok(run(canvas.add_layer(fresh, "empty-layer")))
    result = run(fx.outline_cel(fresh, "empty-layer", 1))
    assert result.startswith("Failed to outline cel:")
    assert "No cel" in result


def test_outline_cel_include_diagonals() -> None:
    fresh = _fresh_sprite("fx-outline-diag")
    result = ok(
        run(fx.outline_cel(fresh, "body", 1, "#000000", include_diagonals=True))
    )
    assert "Outline added" in result


# ── replace_color ─────────────────────────────────────────────────────


def test_replace_color_rejects_bad_hex() -> None:
    fresh = _fresh_sprite("fx-replace-badhex")
    result = run(fx.replace_color(fresh, "body", 1, "nonsense", "#FFFFFF"))
    assert result == "Colors must use #RRGGBB values"

    result = run(fx.replace_color(fresh, "body", 1, "#000000", "nonsense"))
    assert result == "Colors must use #RRGGBB values"


def test_replace_color_rejects_tolerance_out_of_range() -> None:
    fresh = _fresh_sprite("fx-replace-tolerance")
    result = run(fx.replace_color(fresh, "body", 1, "#000000", "#FFFFFF", tolerance=-1))
    assert result == "Tolerance must be between 0 and 255"

    result = run(
        fx.replace_color(fresh, "body", 1, "#000000", "#FFFFFF", tolerance=256)
    )
    assert result == "Tolerance must be between 0 and 255"


def test_replace_color_reports_frame_out_of_range() -> None:
    fresh = _fresh_sprite("fx-replace-oob")
    result = run(fx.replace_color(fresh, "body", 999, "#D04648", "#597DCE"))
    assert result.startswith("Failed to replace color:")
    assert "out of range" in result


def test_replace_color_reports_layer_not_found() -> None:
    fresh = _fresh_sprite("fx-replace-nolayer")
    result = run(fx.replace_color(fresh, "no-such-layer", 1, "#D04648", "#597DCE"))
    assert result.startswith("Failed to replace color:")
    assert "Layer not found" in result


def test_replace_color_reports_no_cel() -> None:
    fresh = _fresh_sprite("fx-replace-nocel")
    ok(run(canvas.add_layer(fresh, "empty-layer")))
    result = run(fx.replace_color(fresh, "empty-layer", 1, "#D04648", "#597DCE"))
    assert result.startswith("Failed to replace color:")
    assert "No cel" in result


def test_replace_color_with_tolerance() -> None:
    fresh = _fresh_sprite("fx-replace-tol-match")
    result = ok(
        run(fx.replace_color(fresh, "body", 1, "#D04648", "#597DCE", tolerance=10))
    )
    assert "Replaced" in result


# ── adjust_hsl ────────────────────────────────────────────────────────


def test_adjust_hsl_rejects_hue_shift_out_of_range() -> None:
    fresh = _fresh_sprite("fx-hsl-hue")
    result = run(fx.adjust_hsl(fresh, "body", 1, hue_shift=-361))
    assert result == "hue_shift must be between -360 and 360"

    result = run(fx.adjust_hsl(fresh, "body", 1, hue_shift=361))
    assert result == "hue_shift must be between -360 and 360"


def test_adjust_hsl_rejects_saturation_shift_out_of_range() -> None:
    fresh = _fresh_sprite("fx-hsl-sat")
    result = run(fx.adjust_hsl(fresh, "body", 1, saturation_shift=-101))
    assert result == "saturation_shift must be between -100 and 100"

    result = run(fx.adjust_hsl(fresh, "body", 1, saturation_shift=101))
    assert result == "saturation_shift must be between -100 and 100"


def test_adjust_hsl_rejects_lightness_shift_out_of_range() -> None:
    fresh = _fresh_sprite("fx-hsl-light")
    result = run(fx.adjust_hsl(fresh, "body", 1, lightness_shift=-101))
    assert result == "lightness_shift must be between -100 and 100"

    result = run(fx.adjust_hsl(fresh, "body", 1, lightness_shift=101))
    assert result == "lightness_shift must be between -100 and 100"


def test_adjust_hsl_reports_frame_out_of_range() -> None:
    fresh = _fresh_sprite("fx-hsl-oob")
    result = run(fx.adjust_hsl(fresh, "body", 999))
    assert result.startswith("Failed to adjust HSL:")
    assert "out of range" in result


def test_adjust_hsl_reports_layer_not_found() -> None:
    fresh = _fresh_sprite("fx-hsl-nolayer")
    result = run(fx.adjust_hsl(fresh, "no-such-layer", 1))
    assert result.startswith("Failed to adjust HSL:")
    assert "Layer not found" in result


def test_adjust_hsl_reports_no_cel() -> None:
    fresh = _fresh_sprite("fx-hsl-nocel")
    ok(run(canvas.add_layer(fresh, "empty-layer")))
    result = run(fx.adjust_hsl(fresh, "empty-layer", 1))
    assert result.startswith("Failed to adjust HSL:")
    assert "No cel" in result


def test_adjust_hsl_success_message_format() -> None:
    fresh = _fresh_sprite("fx-hsl-success")
    result = ok(run(fx.adjust_hsl(fresh, "body", 1, 15, -10, 5)))
    assert "Adjusted HSL (h+15, s-10, l+5)" in result


# ── apply_dither_gradient ─────────────────────────────────────────────


def test_apply_dither_gradient_rejects_non_positive_dims() -> None:
    fresh = _fresh_sprite("fx-dgrad-dims")
    result = run(
        fx.apply_dither_gradient(fresh, "body", 1, 0, 0, 0, 4, "#000000", "#FFFFFF")
    )
    assert result == "Width and height must be > 0"

    result = run(
        fx.apply_dither_gradient(fresh, "body", 1, 0, 0, 4, 0, "#000000", "#FFFFFF")
    )
    assert result == "Width and height must be > 0"


def test_apply_dither_gradient_rejects_bad_hex() -> None:
    fresh = _fresh_sprite("fx-dgrad-badhex")
    result = run(
        fx.apply_dither_gradient(fresh, "body", 1, 0, 0, 4, 4, "nonsense", "#FFFFFF")
    )
    assert result == "Colors must use #RRGGBB values"

    result = run(
        fx.apply_dither_gradient(fresh, "body", 1, 0, 0, 4, 4, "#000000", "nonsense")
    )
    assert result == "Colors must use #RRGGBB values"


def test_apply_dither_gradient_reports_frame_out_of_range() -> None:
    fresh = _fresh_sprite("fx-dgrad-oob")
    result = run(
        fx.apply_dither_gradient(fresh, "body", 999, 0, 0, 4, 4, "#000000", "#FFFFFF")
    )
    assert result.startswith("Failed to apply dither gradient:")
    assert "out of range" in result


def test_apply_dither_gradient_reports_layer_not_found() -> None:
    fresh = _fresh_sprite("fx-dgrad-nolayer")
    result = run(
        fx.apply_dither_gradient(
            fresh, "no-such-layer", 1, 0, 0, 4, 4, "#000000", "#FFFFFF"
        )
    )
    assert result.startswith("Failed to apply dither gradient:")
    assert "Layer not found" in result


def test_apply_dither_gradient_horizontal() -> None:
    fresh = _fresh_sprite("fx-dgrad-horiz")
    result = ok(
        run(
            fx.apply_dither_gradient(
                fresh, "body", 1, 0, 0, 8, 4, "#000000", "#FFFFFF", horizontal=True
            )
        )
    )
    assert "Dithered horizontal gradient" in result


def test_apply_dither_gradient_vertical_default() -> None:
    fresh = _fresh_sprite("fx-dgrad-vert")
    result = ok(
        run(
            fx.apply_dither_gradient(fresh, "body", 1, 0, 0, 4, 8, "#000000", "#FFFFFF")
        )
    )
    assert "Dithered vertical gradient" in result


def test_apply_dither_gradient_no_create_if_missing() -> None:
    fresh = _fresh_sprite("fx-dgrad-nocreate")
    ok(run(canvas.add_layer(fresh, "empty-layer")))
    result = run(
        fx.apply_dither_gradient(
            fresh,
            "empty-layer",
            1,
            0,
            0,
            4,
            4,
            "#000000",
            "#FFFFFF",
            create_if_missing=False,
        )
    )
    assert result.startswith("Failed to apply dither gradient:")
    assert "No cel" in result


# ── apply_dither_pattern ─────────────────────────────────────────────


def test_apply_dither_pattern_rejects_non_positive_dims() -> None:
    fresh = _fresh_sprite("fx-dpat-dims")
    result = run(
        fx.apply_dither_pattern(fresh, "body", 1, 0, 0, 0, 4, "#000000", "#FFFFFF")
    )
    assert result == "Width and height must be > 0"

    result = run(
        fx.apply_dither_pattern(fresh, "body", 1, 0, 0, 4, 0, "#000000", "#FFFFFF")
    )
    assert result == "Width and height must be > 0"


def test_apply_dither_pattern_rejects_density_out_of_range() -> None:
    fresh = _fresh_sprite("fx-dpat-density")
    result = run(
        fx.apply_dither_pattern(
            fresh, "body", 1, 0, 0, 4, 4, "#000000", "#FFFFFF", density=-0.1
        )
    )
    assert result == "density must be between 0.0 and 1.0"

    result = run(
        fx.apply_dither_pattern(
            fresh, "body", 1, 0, 0, 4, 4, "#000000", "#FFFFFF", density=1.1
        )
    )
    assert result == "density must be between 0.0 and 1.0"


def test_apply_dither_pattern_rejects_bad_hex() -> None:
    fresh = _fresh_sprite("fx-dpat-badhex")
    result = run(
        fx.apply_dither_pattern(fresh, "body", 1, 0, 0, 4, 4, "nonsense", "#FFFFFF")
    )
    assert result == "Colors must use #RRGGBB values"

    result = run(
        fx.apply_dither_pattern(fresh, "body", 1, 0, 0, 4, 4, "#000000", "nonsense")
    )
    assert result == "Colors must use #RRGGBB values"


def test_apply_dither_pattern_reports_frame_out_of_range() -> None:
    fresh = _fresh_sprite("fx-dpat-oob")
    result = run(
        fx.apply_dither_pattern(fresh, "body", 999, 0, 0, 4, 4, "#000000", "#FFFFFF")
    )
    assert result.startswith("Failed to apply dither pattern:")
    assert "out of range" in result


def test_apply_dither_pattern_reports_layer_not_found() -> None:
    fresh = _fresh_sprite("fx-dpat-nolayer")
    result = run(
        fx.apply_dither_pattern(
            fresh, "no-such-layer", 1, 0, 0, 4, 4, "#000000", "#FFFFFF"
        )
    )
    assert result.startswith("Failed to apply dither pattern:")
    assert "Layer not found" in result


def test_apply_dither_pattern_density_extremes() -> None:
    fresh = _fresh_sprite("fx-dpat-extremes")
    result_a = ok(
        run(
            fx.apply_dither_pattern(
                fresh, "body", 1, 0, 0, 4, 4, "#000000", "#FFFFFF", density=0.0
            )
        )
    )
    assert "density 0.0" in result_a

    result_b = ok(
        run(
            fx.apply_dither_pattern(
                fresh, "body", 1, 4, 4, 4, 4, "#000000", "#FFFFFF", density=1.0
            )
        )
    )
    assert "density 1.0" in result_b


def test_apply_dither_pattern_no_create_if_missing() -> None:
    fresh = _fresh_sprite("fx-dpat-nocreate")
    ok(run(canvas.add_layer(fresh, "empty-layer")))
    result = run(
        fx.apply_dither_pattern(
            fresh,
            "empty-layer",
            1,
            0,
            0,
            4,
            4,
            "#000000",
            "#FFFFFF",
            create_if_missing=False,
        )
    )
    assert result.startswith("Failed to apply dither pattern:")
    assert "No cel" in result


def test_replace_color_skips_non_count_lines_before_matching() -> None:
    fresh = _fresh_sprite("fx-replace-loop")
    with patch("aseprite_mcp.tools.fx.AsepriteCommand.execute_lua_script_checked") as m:
        m.return_value = (True, "some noise\nCOUNT:3")
        result = run(fx.replace_color(fresh, "body", 1, "#000000", "#FFFFFF"))
    assert "Replaced 3 pixels" in result
