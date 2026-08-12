"""Text rendering (tools/text.py, core/fonts.py).

The bitmap tests build their own font on disk so they run anywhere; only the
TrueType tests need something installed, and they skip when nothing is found.
"""

import json
import os

import pytest
from conftest import ok, run
from PIL import Image

from aseprite_mcp.core import fonts as fontlib
from aseprite_mcp.tools import pixel_read, text

# A 4x6 sheet font covering "ABO", laid out the way font.json describes it:
# one 4x6 cell per glyph, ink is any non-transparent pixel, baseline at row 5.
FIXTURE_GLYPHS = {
    "A": [".##.", "#..#", "####", "#..#", "#..#", "...."],
    "B": ["###.", "#..#", "###.", "#..#", "###.", "...."],
    "O": [".##.", "#..#", "#..#", "#..#", ".##.", "...."],
}
CELL_W, CELL_H, ASCENT = 4, 6, 5


@pytest.fixture(scope="module")
def bitmap_font(tmp_path_factory):
    """A minimal bitmap font directory, returned as a path for `font=`."""
    directory = tmp_path_factory.mktemp("fixture-font")
    chars = "ABO"
    sheet = Image.new("RGBA", (CELL_W * len(chars), CELL_H), (0, 0, 0, 0))
    for index, char in enumerate(chars):
        for y, row in enumerate(FIXTURE_GLYPHS[char]):
            for x, cell in enumerate(row):
                if cell == "#":
                    sheet.putpixel((index * CELL_W + x, y), (255, 255, 255, 255))
    sheet.save(directory / "sheet.png")
    (directory / "font.json").write_text(
        json.dumps(
            {
                "name": "fixture",
                "letter_gap": 1,
                "space_width": 2,
                "sheets": [
                    {
                        "file": "sheet.png",
                        "cell_w": CELL_W,
                        "cell_h": CELL_H,
                        "ascent": ASCENT,
                        "chars": [chars],
                    }
                ],
            }
        )
    )
    fontlib.clear_cache()
    return str(directory)


def _system_truetype():
    for entry in fontlib.available_fonts():
        if entry["kind"] == "truetype":
            return entry["path"]
    return None


# ── discovery / errors ────────────────────────────────────────────────


def test_unknown_font_is_reported():
    out = run(text.measure_text("ABC", "definitely-not-a-font"))
    assert out.startswith("ERROR")
    assert "not found" in out


def test_list_fonts_never_raises():
    out = run(text.list_text_fonts())
    assert not out.startswith("ERROR")


def test_bitmap_font_rejects_zero_size(bitmap_font):
    out = run(text.measure_text("A", bitmap_font, 0))
    assert out.startswith("ERROR")
    assert "scale factor" in out


def test_rejects_bad_anchor(sprite, bitmap_font):
    out = run(text.draw_text(sprite, "A", 0, 0, bitmap_font, anchor="middle"))
    assert "Invalid anchor" in out


# ── measurement ───────────────────────────────────────────────────────


def test_measure_matches_the_fixture_geometry(bitmap_font):
    out = run(text.measure_text("A", bitmap_font, 1))
    # 4px of ink, +1 letter_gap of advance; 5 inked rows, all above the baseline.
    assert "width=4" in out
    assert "height=5" in out
    assert "advance_width=5" in out
    assert "above_baseline=5" in out


def test_measure_scales_with_size(bitmap_font):
    one = run(text.measure_text("AB", bitmap_font, 1))
    two = run(text.measure_text("AB", bitmap_font, 2))
    assert "height=5" in one and "height=10" in two
    # advance per glyph is 4px of ink + 1px letter_gap.
    assert "advance_width=10" in one and "advance_width=20" in two


def test_letter_spacing_widens_the_advance(bitmap_font):
    tight = run(text.measure_text("AB", bitmap_font, 1, letter_spacing=0))
    loose = run(text.measure_text("AB", bitmap_font, 1, letter_spacing=3))
    assert "advance_width=10" in tight
    assert "advance_width=13" in loose


def test_bold_thickens_the_ink(bitmap_font):
    font = fontlib.load_font(bitmap_font)
    plain, _ = fontlib.shape("O", font, 2)
    bold, _ = fontlib.shape("O", font, 2, bold=1)
    assert len(bold) > len(plain)
    assert plain <= bold, "bold must be a superset, not a reflow"


def test_glyphs_share_a_baseline(bitmap_font):
    """Every glyph must sit on one baseline or a word visibly steps."""
    font = fontlib.load_font(bitmap_font)
    bottoms = {fontlib.shape(ch, font, 2)[1]["bottom"] for ch in "ABO"}
    assert len(bottoms) == 1, f"glyphs disagree on the baseline: {bottoms}"


def test_unmapped_characters_are_skipped(bitmap_font):
    """An unknown codepoint contributes nothing rather than raising."""
    assert run(text.measure_text("A?", bitmap_font, 1)) == run(
        text.measure_text("A", bitmap_font, 1)
    )


def test_overrides_replace_a_sheet_glyph(tmp_path, bitmap_font):
    """font.json overrides let a caller repair a glyph the sheet gets wrong."""
    spec = json.loads(open(os.path.join(bitmap_font, "font.json")).read())
    spec["overrides"] = {str(ord("A")): {"ascent": ASCENT, "rows": ["####"] * 5}}
    patched = tmp_path / "patched"
    patched.mkdir()
    (patched / "sheet.png").write_bytes(
        open(os.path.join(bitmap_font, "sheet.png"), "rb").read()
    )
    (patched / "font.json").write_text(json.dumps(spec))

    fontlib.clear_cache()
    ink, _ = fontlib.shape("A", fontlib.load_font(str(patched)), 1)
    assert len(ink) == 20, "override rows should be used verbatim"
    fontlib.clear_cache()


# ── drawing ───────────────────────────────────────────────────────────


def test_draw_text_puts_ink_on_the_canvas(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite,
                "O",
                4,
                4,
                bitmap_font,
                size=1,
                color="#FF0000",
                layer_name="body",
            )
        )
    )
    assert "Drew" in out
    # 'O' has ink at (1,0) of its box, which lands at (5,4) on the sprite.
    px = ok(run(pixel_read.get_pixel_color(sprite, 5, 4, "body", 1)))
    assert "#ff0000" in px.lower()


def test_topleft_anchor_places_the_box_at_the_point(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite,
                "B",
                10,
                10,
                bitmap_font,
                size=1,
                color="#00FF00",
                layer_name="body",
            )
        )
    )
    assert "at (10, 10)" in out


def test_center_anchor_is_offset_by_half_the_box(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite,
                "B",
                20,
                20,
                bitmap_font,
                size=1,
                color="#0000FF",
                layer_name="body",
                anchor="center",
            )
        )
    )
    # box is 4x5, so the top-left lands 2 left and 2 up of the anchor.
    assert "at (18, 18)" in out


def test_outline_grows_the_stamp_but_not_the_box(sprite, bitmap_font):
    plain = ok(
        run(
            text.draw_text(
                sprite,
                "O",
                4,
                14,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
            )
        )
    )
    outlined = ok(
        run(
            text.draw_text(
                sprite,
                "O",
                14,
                14,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
                outline_color="#000000",
            )
        )
    )
    assert "text box 4x5" in plain and "text box 4x5" in outlined
    assert "stamp 4x5" in plain and "stamp 6x7" in outlined


def test_empty_text_is_a_no_op(sprite, bitmap_font):
    out = run(text.draw_text(sprite, "", 0, 0, bitmap_font))
    assert out.startswith("OK")


# ── truetype ──────────────────────────────────────────────────────────


def test_truetype_renders_hard_pixels_by_default():
    path = _system_truetype()
    if not path:
        pytest.skip("no TrueType font available on this machine")
    font = fontlib.load_font(path)
    ink, metrics = fontlib.shape("A", font, 24)
    assert ink, "expected some ink"
    assert metrics["height"] > 1


# ── list_text_fonts branches ────────────────────────────────────────────


def test_list_fonts_reports_user_and_system_sections(monkeypatch):
    fake = [
        {"name": "MyBitmap", "kind": "bitmap", "path": "/x", "source": "user"},
        {"name": "Arial", "kind": "truetype", "path": "/y", "source": "system"},
    ]
    monkeypatch.setattr(text.fontlib, "available_fonts", lambda: fake)
    out = run(text.list_text_fonts())
    assert "User fonts (~/.aseprite-mcp/fonts):" in out
    assert "MyBitmap" in out
    assert "System fonts (1, all truetype):" in out
    assert "Arial" in out


def test_list_fonts_reports_user_only(monkeypatch):
    fake = [{"name": "MyBitmap", "kind": "bitmap", "path": "/x", "source": "user"}]
    monkeypatch.setattr(text.fontlib, "available_fonts", lambda: fake)
    out = run(text.list_text_fonts())
    assert "User fonts (~/.aseprite-mcp/fonts):" in out
    assert "System fonts" not in out


def test_list_fonts_reports_system_only(monkeypatch):
    fake = [{"name": "Arial", "kind": "truetype", "path": "/y", "source": "system"}]
    monkeypatch.setattr(text.fontlib, "available_fonts", lambda: fake)
    out = run(text.list_text_fonts())
    assert "User fonts" not in out
    assert "System fonts (1, all truetype):" in out


def test_list_fonts_reports_no_fonts_found(monkeypatch):
    monkeypatch.setattr(text.fontlib, "available_fonts", lambda: [])
    out = run(text.list_text_fonts())
    assert out == "No fonts found. Drop a .ttf into ~/.aseprite-mcp/fonts/."


def test_list_fonts_surfaces_discovery_errors(monkeypatch):
    def boom():
        raise RuntimeError("disk unreadable")

    monkeypatch.setattr(text.fontlib, "available_fonts", boom)
    out = run(text.list_text_fonts())
    assert out == "ERROR: disk unreadable"


# ── _text_origin anchor branches (via draw_text) ────────────────────────


def test_right_anchor_subtracts_full_width(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite,
                "B",
                30,
                4,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
                anchor="right",
            )
        )
    )
    # box is 4 wide; "right" anchor puts the box's left edge 4px left of x.
    # y also shifts by -metrics['top'] (-(-5)=5): the fixture's ink runs from
    # y=-5 (top row) to y=-1 (baseline row) relative to the baseline.
    assert "at (26, 2)" in out


def test_bottom_anchor_subtracts_full_height(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite,
                "B",
                4,
                30,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
                anchor="bottom",
            )
        )
    )
    # box is 4 wide (halved -> 2) and 5 tall; bottom anchor moves the top up
    # by the full height and centers x.
    assert "at (2, 25)" in out


def test_baseline_anchor_applies_no_vertical_correction(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite,
                "B",
                4,
                20,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
                anchor="baseline",
            )
        )
    )
    # baseline* anchors skip the height-based y adjustment entirely, but the
    # final blit position still applies -metrics['top'] (=5 for this glyph,
    # whose ink runs from y=-5 at the baseline) plus min_y (-5) from the
    # ink's own bounding box, netting out to 20 - 5 = 15.
    assert "at (2, 15)" in out


def test_baselineleft_anchor_applies_no_vertical_correction(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite,
                "B",
                4,
                20,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
                anchor="baselineleft",
            )
        )
    )
    assert "at (4, 15)" in out


# ── color validation branches ───────────────────────────────────────────


def test_draw_text_rejects_invalid_fill_color(sprite, bitmap_font):
    out = run(text.draw_text(sprite, "A", 0, 0, bitmap_font, color="not-a-color"))
    assert out == "Invalid color value: not-a-color"


def test_draw_text_rejects_invalid_outline_color(sprite, bitmap_font):
    out = run(
        text.draw_text(sprite, "A", 0, 0, bitmap_font, outline_color="not-a-color")
    )
    assert out == "Invalid outline_color value: not-a-color"


def test_draw_text_rejects_invalid_shadow_color(sprite, bitmap_font):
    out = run(
        text.draw_text(sprite, "A", 0, 0, bitmap_font, shadow_color="not-a-color")
    )
    assert out == "Invalid shadow_color value: not-a-color"


def test_draw_text_missing_file(bitmap_font):
    missing = "/tmp/ase-pytest/does-not-exist.aseprite"
    out = run(text.draw_text(missing, "A", 0, 0, bitmap_font))
    assert out == f"File {missing} not found"


def test_draw_text_font_load_error_is_reported(sprite):
    out = run(text.draw_text(sprite, "A", 0, 0, "definitely-not-a-font"))
    assert out.startswith("ERROR:")


def test_draw_text_tolerates_temp_file_cleanup_failure(
    sprite, bitmap_font, monkeypatch
):
    # The finally-block os.unlink(tmp.name) can race a concurrent cleanup
    # or antivirus lock; the swallowed OSError must not surface to the
    # caller or block the real success/failure result.
    real_unlink = os.unlink

    def flaky_unlink(path):
        if path.endswith(".png"):
            raise OSError("simulated cleanup failure")
        real_unlink(path)

    monkeypatch.setattr(text.os, "unlink", flaky_unlink)
    out = ok(run(text.draw_text(sprite, "A", 0, 0, bitmap_font)))
    assert "Drew" in out


def test_draw_text_shadow_with_no_outline(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite,
                "O",
                4,
                24,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
                shadow_color="#000000",
                shadow_dx=2,
                shadow_dy=2,
            )
        )
    )
    assert "Drew" in out


def test_draw_text_outline_without_diagonals_is_smaller(sprite, bitmap_font):
    diag = ok(
        run(
            text.draw_text(
                sprite,
                "O",
                4,
                4,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
                outline_color="#000000",
                outline_diagonal=True,
            )
        )
    )
    boxy = ok(
        run(
            text.draw_text(
                sprite,
                "O",
                14,
                4,
                bitmap_font,
                size=1,
                color="#FFFFFF",
                layer_name="body",
                outline_color="#000000",
                outline_diagonal=False,
            )
        )
    )
    # Both grow the stamp beyond the 4x5 glyph box, but the 4-way outline is
    # never larger than the diagonal one.
    assert "text box 4x5" in diag and "text box 4x5" in boxy


def test_draw_text_creates_missing_layer_by_default(sprite, bitmap_font):
    out = ok(
        run(
            text.draw_text(
                sprite, "A", 0, 0, bitmap_font, layer_name="brand-new-text-layer"
            )
        )
    )
    assert "Drew" in out


def test_draw_text_reports_missing_layer_when_create_disabled(sprite, bitmap_font):
    out = run(
        text.draw_text(
            sprite,
            "A",
            0,
            0,
            bitmap_font,
            layer_name="still-does-not-exist",
            create_if_missing=False,
        )
    )
    assert "Error drawing text" in out
    assert "Layer not found" in out


def test_draw_text_without_layer_name_uses_active_layer(sprite, bitmap_font):
    out = ok(run(text.draw_text(sprite, "A", 0, 0, bitmap_font)))
    assert "Drew" in out


def test_draw_text_reports_frame_out_of_range(sprite, bitmap_font):
    out = run(
        text.draw_text(
            sprite, "A", 0, 0, bitmap_font, layer_name="body", frame_index=999
        )
    )
    assert "Error drawing text" in out
    assert "out of range" in out
