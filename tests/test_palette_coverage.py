"""Coverage tests for palette.py: validation, error, and branch paths.

Ordering note: set_color_mode / quantize_to_palette run last since they
mutate the shared module-scoped sprite's palette and color mode.
"""

import json
from unittest.mock import patch

from conftest import BASE, ok, run

from aseprite_mcp.tools import canvas, drawing, palette


def _fresh_sprite(name: str) -> str:
    path = f"{BASE}/{name}.aseprite"
    ok(run(canvas.create_canvas(16, 16, path)))
    ok(run(canvas.add_layer(path, "body")))
    return path


# ── missing-file guards ──────────────────────────────────────────────────


def test_get_palette_missing_file() -> None:
    result = run(palette.get_palette(f"{BASE}/does-not-exist.aseprite"))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_set_palette_missing_file() -> None:
    result = run(palette.set_palette(f"{BASE}/does-not-exist.aseprite", ["#000000"]))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_remap_colors_missing_file() -> None:
    result = run(
        palette.remap_colors_in_cel_range(
            f"{BASE}/does-not-exist.aseprite",
            "body",
            1,
            1,
            [{"from": "#000000", "to": "#FFFFFF"}],
        )
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_quantize_to_palette_missing_file() -> None:
    result = run(palette.quantize_to_palette(f"{BASE}/does-not-exist.aseprite"))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


def test_set_color_mode_missing_file() -> None:
    result = run(palette.set_color_mode(f"{BASE}/does-not-exist.aseprite", "rgb"))
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


# ── get_palette ───────────────────────────────────────────────────────


def test_get_palette_returns_json_array() -> None:
    fresh = _fresh_sprite("palette-get")
    result = ok(run(palette.get_palette(fresh)))
    colors = json.loads(result)
    assert isinstance(colors, list)
    assert all(c.startswith("#") and len(c) == 7 for c in colors)


# ── set_palette ───────────────────────────────────────────────────────


def test_set_palette_rejects_empty_list() -> None:
    fresh = _fresh_sprite("palette-set-empty")
    result = run(palette.set_palette(fresh, []))
    assert result == "Colors list cannot be empty"


def test_set_palette_rejects_bad_hex() -> None:
    fresh = _fresh_sprite("palette-set-bad")
    result = run(palette.set_palette(fresh, ["not-a-color"]))
    assert result == "Colors must use #RRGGBB values"


def test_set_palette_success() -> None:
    fresh = _fresh_sprite("palette-set-ok")
    colors = ["#000000", "#FFFFFF", "#FF0000"]
    result = ok(run(palette.set_palette(fresh, colors)))
    assert result == f"Palette set with 3 colors in {fresh}"


# ── remap_colors_in_cel_range ────────────────────────────────────────────


def test_remap_colors_rejects_empty_mappings() -> None:
    fresh = _fresh_sprite("palette-remap-empty")
    result = run(palette.remap_colors_in_cel_range(fresh, "body", 1, 1, []))
    assert result == "Mappings list cannot be empty"


def test_remap_colors_rejects_bad_hex() -> None:
    fresh = _fresh_sprite("palette-remap-bad")
    result = run(
        palette.remap_colors_in_cel_range(
            fresh, "body", 1, 1, [{"from": "nonsense", "to": "#FFFFFF"}]
        )
    )
    assert result == "Mappings must use #RRGGBB colors"

    result = run(
        palette.remap_colors_in_cel_range(
            fresh, "body", 1, 1, [{"from": "#000000", "to": "nonsense"}]
        )
    )
    assert result == "Mappings must use #RRGGBB colors"


def test_remap_colors_reports_frame_range_out_of_bounds() -> None:
    fresh = _fresh_sprite("palette-remap-oob")
    result = run(
        palette.remap_colors_in_cel_range(
            fresh, "body", 1, 999, [{"from": "#000000", "to": "#FFFFFF"}]
        )
    )
    assert result.startswith("Failed to remap colors:")
    assert "out of bounds" in result


def test_remap_colors_reports_layer_not_found() -> None:
    fresh = _fresh_sprite("palette-remap-nolayer")
    result = run(
        palette.remap_colors_in_cel_range(
            fresh, "no-such-layer", 1, 1, [{"from": "#000000", "to": "#FFFFFF"}]
        )
    )
    assert result.startswith("Failed to remap colors:")
    assert "Layer not found" in result


def test_remap_colors_success() -> None:
    fresh = _fresh_sprite("palette-remap-ok")
    ok(
        run(
            drawing.draw_rectangle_at(
                fresh, "body", 1, 0, 0, 4, 4, "#D04648", fill=True
            )
        )
    )
    result = ok(
        run(
            palette.remap_colors_in_cel_range(
                fresh, "body", 1, 1, [{"from": "#D04648", "to": "#597DCE"}]
            )
        )
    )
    assert "Remapped colors on 'body' frames 1-1" in result


def test_remap_colors_with_source_frame_and_create_missing_cels() -> None:
    fresh = _fresh_sprite("palette-remap-source")
    ok(run(canvas.add_frame(fresh)))
    ok(
        run(
            drawing.draw_rectangle_at(
                fresh, "body", 1, 0, 0, 4, 4, "#D04648", fill=True
            )
        )
    )
    result = ok(
        run(
            palette.remap_colors_in_cel_range(
                fresh,
                "body",
                1,
                2,
                [{"from": "#D04648", "to": "#597DCE"}],
                create_missing_cels=True,
                source_frame_index=1,
            )
        )
    )
    assert "Remapped colors on 'body' frames 1-2" in result


def test_remap_colors_reports_source_frame_out_of_range() -> None:
    fresh = _fresh_sprite("palette-remap-source-oob")
    result = run(
        palette.remap_colors_in_cel_range(
            fresh,
            "body",
            1,
            1,
            [{"from": "#000000", "to": "#FFFFFF"}],
            source_frame_index=999,
        )
    )
    assert result.startswith("Failed to remap colors:")
    assert "Source frame out of range" in result


# ── apply_palette_preset ────────────────────────────────────────────────


def test_apply_palette_preset_missing_file_propagates_set_palette_error() -> None:
    # apply_palette_preset resolves colors first, then delegates to
    # set_palette; on a missing file it returns set_palette's raw "File
    # ... not found" message (which does not start with "Palette set").
    result = run(
        palette.apply_palette_preset(f"{BASE}/does-not-exist.aseprite", "gameboy")
    )
    assert result == f"File {BASE}/does-not-exist.aseprite not found"


# ── generate_color_ramp ──────────────────────────────────────────────────


def test_generate_color_ramp_rejects_bad_color() -> None:
    result = run(palette.generate_color_ramp("not-a-color"))
    assert result == "Invalid color value: not-a-color"


def test_generate_color_ramp_rejects_steps_out_of_range() -> None:
    result = run(palette.generate_color_ramp("#D04648", steps=1))
    assert result == "steps must be between 2 and 16"

    result = run(palette.generate_color_ramp("#D04648", steps=17))
    assert result == "steps must be between 2 and 16"


def test_generate_color_ramp_rejects_lightness_range_out_of_bounds() -> None:
    result = run(palette.generate_color_ramp("#D04648", lightness_range=-0.1))
    assert result == "lightness_range must be between 0 and 1"

    result = run(palette.generate_color_ramp("#D04648", lightness_range=1.1))
    assert result == "lightness_range must be between 0 and 1"


def test_generate_color_ramp_two_steps() -> None:
    # Smallest allowed step count (validation rejects steps < 2), giving
    # mid == 0.5 and t values of exactly -0.5/+0.5. Note the ternary's
    # `else 0` arm (steps > 1 false) is unreachable: validation guarantees
    # steps >= 2, so that branch can never execute — see report.
    ramp = json.loads(run(palette.generate_color_ramp("#D04648", steps=2)))
    assert len(ramp) == 2


# ── quantize_to_palette ──────────────────────────────────────────────────


def test_quantize_to_palette_reports_layer_not_found() -> None:
    fresh = _fresh_sprite("palette-quantize-nolayer")
    result = run(palette.quantize_to_palette(fresh, layer_name="no-such-layer"))
    assert result.startswith("Failed to quantize:")
    assert "Layer not found" in result


def test_quantize_to_palette_reports_frame_range_out_of_bounds() -> None:
    fresh = _fresh_sprite("palette-quantize-oob")
    result = run(palette.quantize_to_palette(fresh, start_frame=1, end_frame=999))
    assert result.startswith("Failed to quantize:")
    assert "out of bounds" in result


def test_quantize_to_palette_specific_layer() -> None:
    fresh = _fresh_sprite("palette-quantize-layer")
    ok(
        run(
            drawing.draw_rectangle_at(
                fresh, "body", 1, 0, 0, 4, 4, "#D04648", fill=True
            )
        )
    )
    ok(run(palette.apply_palette_preset(fresh, "gameboy")))
    result = ok(run(palette.quantize_to_palette(fresh, layer_name="body")))
    assert "Quantized" in result


# ── set_color_mode ───────────────────────────────────────────────────────


def test_set_color_mode_rejects_unknown_mode(sprite: str) -> None:
    result = run(palette.set_color_mode(sprite, "cmyk"))
    assert result == "mode must be 'rgb', 'grayscale', or 'indexed'"


def test_set_color_mode_grayscale_roundtrip(sprite: str) -> None:
    ok(run(palette.set_color_mode(sprite, "grayscale")))
    result = ok(run(palette.set_color_mode(sprite, "rgb")))
    assert result == f"Color mode set to rgb in {sprite}"


# ── mocked execute_lua_script_checked: process-level subprocess failures ──


def test_get_palette_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.palette.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(palette.get_palette(sprite))
    assert result == "Failed to get palette: boom"


def test_set_palette_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.palette.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(palette.set_palette(sprite, ["#FF0000"]))
    assert result == "Failed to set palette: boom"


def test_set_color_mode_reports_subprocess_failure(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.palette.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (False, "boom")
        result = run(palette.set_color_mode(sprite, "rgb"))
    assert result == "Failed to set color mode: boom"


def test_quantize_to_palette_skips_non_count_lines_before_matching(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.palette.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "some noise\nCOUNT:9")
        result = run(palette.quantize_to_palette(sprite))
    assert "Quantized 9 pixels" in result
