"""Unit tests for aseprite_mcp/core/fonts.py internals.

Unlike the rest of tests/, this module never touches a real Aseprite
process: fonts.py is pure Python + Pillow, so these are plain synchronous
unit tests that construct BitmapFont/TrueTypeFont objects directly and
call the module's free functions. tests/test_text.py already exercises
this module indirectly through the draw_text/measure_text/list_text_fonts
MCP tools; this file covers what only shows up by poking fonts.py itself
(malformed descriptors, the "dark" ink rule, discovery/caching, TrueType
rasterisation details).

A real system TrueType font (Liberation Sans, shipped by the
`liberation` package) is used for the TrueType-backed tests; they skip
if it isn't present rather than failing the suite on a machine without it.
"""

import json
import os
import shutil
import tempfile

import pytest
from PIL import Image

from aseprite_mcp.core import fonts as fontlib

SYSTEM_TTF = "/usr/share/fonts/liberation/LiberationSans-Regular.ttf"
requires_system_ttf = pytest.mark.skipif(
    not os.path.exists(SYSTEM_TTF), reason="no Liberation Sans on this machine"
)


@pytest.fixture(autouse=True)
def _clean_font_cache():
    """`_loaded` is a module-global cache; don't let it leak across tests."""
    fontlib.clear_cache()
    yield
    fontlib.clear_cache()


def _write_font_json(directory, spec):
    with open(os.path.join(directory, "font.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(spec))


def _blank_sheet(directory, filename, size=(4, 4)):
    Image.new("RGBA", size, (0, 0, 0, 0)).save(os.path.join(directory, filename))


# ---------------------------------------------------------------------------
# BitmapFont.__init__ error handling
# ---------------------------------------------------------------------------


def test_malformed_json_raises_font_error(tmp_path):
    (tmp_path / "font.json").write_text("{not valid json")
    with pytest.raises(fontlib.FontError, match="Could not read"):
        fontlib.BitmapFont(str(tmp_path))


def test_missing_font_json_raises_font_error(tmp_path):
    with pytest.raises(fontlib.FontError, match="Could not read"):
        fontlib.BitmapFont(str(tmp_path))


def test_no_sheets_key_raises_font_error(tmp_path):
    _write_font_json(tmp_path, {"name": "x"})
    with pytest.raises(fontlib.FontError, match="declares no sheets"):
        fontlib.BitmapFont(str(tmp_path))


def test_empty_sheets_list_raises_font_error(tmp_path):
    _write_font_json(tmp_path, {"name": "x", "sheets": []})
    with pytest.raises(fontlib.FontError, match="declares no sheets"):
        fontlib.BitmapFont(str(tmp_path))


def test_missing_sheet_png_raises_font_error(tmp_path):
    _write_font_json(
        tmp_path,
        {
            "name": "x",
            "sheets": [
                {
                    "file": "missing.png",
                    "cell_w": 4,
                    "cell_h": 4,
                    "ascent": 3,
                    "chars": ["A"],
                }
            ],
        },
    )
    with pytest.raises(fontlib.FontError, match="Bad sheet"):
        fontlib.BitmapFont(str(tmp_path))


def test_sheet_missing_file_key_raises_font_error(tmp_path):
    _write_font_json(
        tmp_path,
        {
            "name": "x",
            "sheets": [{"cell_w": 4, "cell_h": 4, "ascent": 3, "chars": ["A"]}],
        },
    )
    with pytest.raises(fontlib.FontError, match="Bad sheet"):
        fontlib.BitmapFont(str(tmp_path))


def test_sheet_missing_cell_w_raises_bare_key_error(tmp_path):
    """Known bug: cell_w/cell_h/ascent are read with int(sheet[...]) OUTSIDE
    the try/except that wraps sheet loading, so a missing key surfaces as a
    bare KeyError instead of the module's own FontError. Documented here as
    current behaviour, not fixed (see report)."""
    _blank_sheet(tmp_path, "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "x",
            "sheets": [{"file": "s.png", "cell_h": 4, "ascent": 3, "chars": ["A"]}],
        },
    )
    with pytest.raises(KeyError):
        fontlib.BitmapFont(str(tmp_path))


# ---------------------------------------------------------------------------
# BitmapFont.glyph() / codepoint indexing
# ---------------------------------------------------------------------------


def _simple_bitmap_font(tmp_path, chars="A", extra_sheet_kwargs=None):
    """One 4x4 cell with a single lit pixel at (0, 0), mapped to `chars`."""
    img = Image.new("RGBA", (4 * len(chars), 4), (0, 0, 0, 0))
    px = img.load()
    for i in range(len(chars)):
        px[i * 4, 0] = (255, 255, 255, 255)
    img.save(tmp_path / "s.png")
    sheet = {"file": "s.png", "cell_w": 4, "cell_h": 4, "ascent": 3, "chars": [chars]}
    if extra_sheet_kwargs:
        sheet.update(extra_sheet_kwargs)
    _write_font_json(tmp_path, {"name": "simple", "sheets": [sheet]})
    return fontlib.BitmapFont(str(tmp_path))


def test_glyph_returns_none_for_unmapped_codepoint(tmp_path):
    font = _simple_bitmap_font(tmp_path)
    assert font.glyph(ord("Z")) is None


def test_glyph_cache_hits_for_both_present_and_absent(tmp_path):
    font = _simple_bitmap_font(tmp_path)
    first_hit = font.glyph(ord("A"))
    second_hit = font.glyph(ord("A"))
    assert first_hit is second_hit  # cached object, not just equal
    first_miss = font.glyph(ord("Z"))
    second_miss = font.glyph(ord("Z"))
    assert first_miss is None and second_miss is None
    assert ord("Z") in font._cache


def test_null_codepoint_in_chars_row_is_not_indexed(tmp_path):
    img = Image.new("RGBA", (8, 4), (0, 0, 0, 0))
    img.save(tmp_path / "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "nul",
            "sheets": [
                {
                    "file": "s.png",
                    "cell_w": 4,
                    "cell_h": 4,
                    "ascent": 3,
                    "chars": ["\x00A"],
                }
            ],
        },
    )
    font = fontlib.BitmapFont(str(tmp_path))
    assert 0 not in font._index
    assert ord("A") in font._index


def test_first_sheet_wins_for_duplicate_codepoint(tmp_path):
    img1 = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    img1.load()[0, 0] = (255, 255, 255, 255)
    img1.save(tmp_path / "s1.png")
    img2 = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    img2.load()[1, 1] = (255, 255, 255, 255)
    img2.save(tmp_path / "s2.png")
    _write_font_json(
        tmp_path,
        {
            "name": "dup",
            "sheets": [
                {
                    "file": "s1.png",
                    "cell_w": 4,
                    "cell_h": 4,
                    "ascent": 3,
                    "chars": ["A"],
                },
                {
                    "file": "s2.png",
                    "cell_w": 4,
                    "cell_h": 4,
                    "ascent": 3,
                    "chars": ["A"],
                },
            ],
        },
    )
    font = fontlib.BitmapFont(str(tmp_path))
    assert font.glyph(ord("A")).ink == {(0, 0)}


# ---------------------------------------------------------------------------
# BitmapFont._read_cell() via glyph() - ink_rule / advance combinations
# ---------------------------------------------------------------------------


def test_dark_ink_rule_reads_box_and_ink(tmp_path):
    """White (255,255,255,255) background box, near-black ink inside it,
    with ink touching the cell's leftmost column so box_h detection works."""
    img = Image.new("RGBA", (6, 6), (255, 255, 255, 255))
    px = img.load()
    for y in range(4):
        for x in range(3):
            px[x, y] = (0, 0, 0, 255)
    img.save(tmp_path / "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "dark",
            "sheets": [
                {
                    "file": "s.png",
                    "cell_w": 6,
                    "cell_h": 6,
                    "ascent": 5,
                    "ink_rule": "dark",
                    "advance": "box",
                    "chars": ["A"],
                }
            ],
        },
    )
    font = fontlib.BitmapFont(str(tmp_path))
    glyph = font.glyph(ord("A"))
    assert glyph.height == 4
    assert glyph.advance == 3  # box_w, matches the empirically-measured box
    assert (0, 0) in glyph.ink and (2, 3) in glyph.ink
    assert (3, 0) not in glyph.ink  # outside the ink region


def test_dark_ink_rule_with_advance_ink(tmp_path):
    img = Image.new("RGBA", (6, 6), (255, 255, 255, 255))
    px = img.load()
    for y in range(4):
        for x in range(3):
            px[x, y] = (0, 0, 0, 255)
    img.save(tmp_path / "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "dark-ink",
            "sheets": [
                {
                    "file": "s.png",
                    "cell_w": 6,
                    "cell_h": 6,
                    "ascent": 5,
                    "ink_rule": "dark",
                    "advance": "ink",
                    "chars": ["A"],
                }
            ],
        },
    )
    font = fontlib.BitmapFont(str(tmp_path))
    glyph = font.glyph(ord("A"))
    # advance = ink_width (3) + default letter_gap (1)
    assert glyph.advance == 4


def test_dark_ink_rule_blank_leftmost_column_yields_empty_box(tmp_path):
    """Known bug: _read_cell's dark-mode box_h scan only probes column `ox`
    (the cell's leftmost pixel) to find where the white background resumes.
    If a glyph's ink does not touch the leftmost column, is_background(ox, ...)
    reports background from row 0 onward, box_h comes out 0, and a visibly
    inked cell rasterises to *no* ink at all. Documented as current
    behaviour, not fixed (see report)."""
    img = Image.new("RGBA", (6, 6), (255, 255, 255, 255))
    px = img.load()
    for y in range(1, 5):
        for x in range(1, 5):
            px[x, y] = (0, 0, 0, 255)
    img.save(tmp_path / "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "dark-bug",
            "sheets": [
                {
                    "file": "s.png",
                    "cell_w": 6,
                    "cell_h": 6,
                    "ascent": 5,
                    "ink_rule": "dark",
                    "advance": "box",
                    "chars": ["A"],
                }
            ],
        },
    )
    font = fontlib.BitmapFont(str(tmp_path))
    glyph = font.glyph(ord("A"))
    assert glyph.ink == set()
    assert glyph.height == 0


def test_alpha_ink_rule_blank_cell_advance_box(tmp_path):
    """advance='box' on an all-transparent (blank) cell: box_w is the full
    cell width (truthy), so the space_width fallback is NOT used."""
    _blank_sheet(tmp_path, "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "blank-box",
            "space_width": 7,
            "sheets": [
                {
                    "file": "s.png",
                    "cell_w": 4,
                    "cell_h": 4,
                    "ascent": 3,
                    "advance": "box",
                    "chars": [" "],
                }
            ],
        },
    )
    font = fontlib.BitmapFont(str(tmp_path))
    glyph = font.glyph(ord(" "))
    assert glyph.ink == set()
    assert glyph.advance == 4  # cell_w, not space_width


def test_alpha_ink_rule_blank_cell_advance_ink_uses_space_width(tmp_path):
    """advance='ink' on a blank cell: ink_width is 0 (falsy), so the
    space_width + letter_gap fallback applies."""
    _blank_sheet(tmp_path, "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "blank-ink",
            "space_width": 7,
            "letter_gap": 2,
            "sheets": [
                {
                    "file": "s.png",
                    "cell_w": 4,
                    "cell_h": 4,
                    "ascent": 3,
                    "advance": "ink",
                    "chars": [" "],
                }
            ],
        },
    )
    font = fontlib.BitmapFont(str(tmp_path))
    glyph = font.glyph(ord(" "))
    assert glyph.advance == 9  # space_width(7) + letter_gap(2)


# ---------------------------------------------------------------------------
# BitmapFont.layout()
# ---------------------------------------------------------------------------


def test_layout_empty_string(tmp_path):
    font = _simple_bitmap_font(tmp_path)
    ink, advance = font.layout("", scale=1, letter_spacing=0)
    assert ink == set()
    assert advance == 0


def test_layout_unknown_chars_contribute_nothing(tmp_path):
    font = _simple_bitmap_font(tmp_path, chars="A")
    only_known, adv_known = font.layout("A", scale=1, letter_spacing=0)
    with_unknown, adv_with_unknown = font.layout("A??", scale=1, letter_spacing=0)
    assert only_known == with_unknown
    assert adv_known == adv_with_unknown


def test_layout_scale_multiplies_ink_and_advance(tmp_path):
    font = _simple_bitmap_font(tmp_path, chars="A")
    ink1, adv1 = font.layout("A", scale=1, letter_spacing=0)
    ink2, adv2 = font.layout("A", scale=2, letter_spacing=0)
    assert len(ink2) == len(ink1) * 4  # each source pixel becomes a 2x2 block
    assert adv2 == adv1 * 2


def test_layout_letter_spacing_is_additive_per_glyph(tmp_path):
    font = _simple_bitmap_font(tmp_path, chars="A")
    _, adv_tight = font.layout("AA", scale=1, letter_spacing=0)
    _, adv_loose = font.layout("AA", scale=1, letter_spacing=3)
    assert (
        adv_loose == adv_tight + 3
    )  # spacing added once, after the final glyph subtracted


# ---------------------------------------------------------------------------
# _glyph_from_rows() (overrides)
# ---------------------------------------------------------------------------


def test_glyph_from_rows_explicit_ascent():
    glyph = fontlib._glyph_from_rows(["##", ".#", ".."], ascent=5, letter_gap=1)
    assert glyph.ascent == 5
    assert glyph.height == 3
    assert glyph.advance == 3  # width(2) + letter_gap(1)
    assert glyph.ink == {(0, 0), (1, 0), (1, 1)}


def test_glyph_from_rows_default_ascent_is_row_count():
    glyph = fontlib._glyph_from_rows(["##", ".#", ".."], ascent=None, letter_gap=1)
    assert glyph.ascent == 3


def test_glyph_from_rows_treats_space_as_empty():
    glyph = fontlib._glyph_from_rows(["# #"], ascent=1, letter_gap=0)
    assert glyph.ink == {(0, 0), (2, 0)}


def test_overrides_are_indexed_by_codepoint(tmp_path):
    img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    img.save(tmp_path / "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "with-override",
            "sheets": [
                {"file": "s.png", "cell_w": 4, "cell_h": 4, "ascent": 3, "chars": ["A"]}
            ],
            "overrides": {str(ord("Q")): {"rows": ["##", "##"]}},
        },
    )
    font = fontlib.BitmapFont(str(tmp_path))
    glyph = font.glyph(ord("Q"))
    assert glyph is not None
    assert glyph.ink == {(0, 0), (1, 0), (0, 1), (1, 1)}
    # an override takes priority even if the sheet also indexes the codepoint.
    assert font._overrides[ord("Q")] is glyph


# ---------------------------------------------------------------------------
# TrueTypeFont
# ---------------------------------------------------------------------------


@requires_system_ttf
def test_truetype_name_is_derived_from_filename():
    font = fontlib.TrueTypeFont(SYSTEM_TTF)
    assert font.name == "LiberationSans-Regular"


@requires_system_ttf
def test_truetype_load_error_wraps_in_font_error():
    font = fontlib.TrueTypeFont("/nonexistent/path/font.ttf")
    with pytest.raises(fontlib.FontError, match="Could not load font"):
        font.layout("A", 16, 0)


@requires_system_ttf
def test_truetype_load_error_on_non_font_file(tmp_path):
    bogus = tmp_path / "notafont.ttf"
    bogus.write_text("not a font")
    font = fontlib.TrueTypeFont(str(bogus))
    with pytest.raises(fontlib.FontError, match="Could not load font"):
        font.layout("A", 16, 0)


@requires_system_ttf
def test_truetype_layout_empty_string():
    font = fontlib.TrueTypeFont(SYSTEM_TTF)
    ink, advance = font.layout("", 16, 0)
    assert ink == set()
    assert advance == 0


@requires_system_ttf
def test_truetype_letter_spacing_widens_advance():
    font = fontlib.TrueTypeFont(SYSTEM_TTF)
    _, adv_tight = font.layout("Hi", 16, 0)
    _, adv_loose = font.layout("Hi", 16, 5)
    assert adv_loose > adv_tight


@requires_system_ttf
def test_truetype_antialias_produces_more_ink_than_hard_threshold():
    font = fontlib.TrueTypeFont(SYSTEM_TTF)
    ink_aa, _ = font.layout("A", 24, 0, antialias=True)
    ink_hard, _ = font.layout("A", 24, 0, antialias=False, threshold=128)
    assert len(ink_aa) > len(ink_hard)


@requires_system_ttf
def test_truetype_threshold_changes_ink_count():
    font = fontlib.TrueTypeFont(SYSTEM_TTF)
    ink_low, _ = font.layout("A", 24, 0, antialias=False, threshold=10)
    ink_high, _ = font.layout("A", 24, 0, antialias=False, threshold=250)
    assert len(ink_low) >= len(ink_high)


@requires_system_ttf
def test_truetype_layout_with_and_without_letter_spacing_agree_on_single_char():
    """The letter_spacing=0 fast path and the per-char loop (spacing>0) must
    rasterise a lone character identically once the trailing spacing is
    subtracted back out."""
    font = fontlib.TrueTypeFont(SYSTEM_TTF)
    ink_fast, adv_fast = font.layout("A", 20, 0)
    ink_loop, adv_loop = font.layout("A", 20, 7)
    assert ink_fast == ink_loop
    assert adv_fast == adv_loop  # letter_spacing after the only glyph is stripped


# ---------------------------------------------------------------------------
# discovery: _iter_user_fonts / _iter_system_fonts / available_fonts
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_font_dirs(monkeypatch):
    """Point FONT_DIR/_SYSTEM_FONT_DIRS at throwaway directories so discovery
    tests don't depend on this machine's real ~/.aseprite-mcp/fonts or
    top-level system font layout."""
    user_dir = tempfile.mkdtemp()
    monkeypatch.setattr(fontlib, "FONT_DIR", user_dir)
    monkeypatch.setattr(fontlib, "_SYSTEM_FONT_DIRS", ())
    yield user_dir
    shutil.rmtree(user_dir, ignore_errors=True)


def test_iter_user_fonts_missing_dir_yields_nothing(monkeypatch):
    monkeypatch.setattr(fontlib, "FONT_DIR", "/no/such/dir/at/all")
    assert list(fontlib._iter_user_fonts()) == []


def test_iter_user_fonts_skips_dirs_without_font_json_and_stray_files(
    isolated_font_dirs,
):
    user_dir = isolated_font_dirs
    os.makedirs(os.path.join(user_dir, "not_a_font_dir"))
    with open(os.path.join(user_dir, "readme.txt"), "w") as fh:
        fh.write("hi")
    assert list(fontlib._iter_user_fonts()) == []


@requires_system_ttf
def test_iter_user_fonts_finds_bitmap_dir_and_ttf_file(isolated_font_dirs):
    user_dir = isolated_font_dirs
    bmp_dir = os.path.join(user_dir, "mybitmap")
    os.makedirs(bmp_dir)
    _blank_sheet(bmp_dir, "s.png")
    _write_font_json(
        bmp_dir,
        {
            "name": "mybitmap",
            "sheets": [
                {"file": "s.png", "cell_w": 4, "cell_h": 4, "ascent": 3, "chars": ["A"]}
            ],
        },
    )
    shutil.copy(SYSTEM_TTF, os.path.join(user_dir, "MyTTF.ttf"))

    found = {(name, kind) for name, _path, kind in fontlib._iter_user_fonts()}
    assert ("mybitmap", "bitmap") in found
    assert ("MyTTF", "truetype") in found


def test_iter_system_fonts_skips_unreadable_dir(monkeypatch):
    monkeypatch.setattr(fontlib, "_SYSTEM_FONT_DIRS", ("/fake/protected",))
    monkeypatch.setattr(
        fontlib.os.path, "isdir", lambda path: path == "/fake/protected"
    )

    def raising_listdir(path):
        raise OSError("denied")

    monkeypatch.setattr(fontlib.os, "listdir", raising_listdir)
    assert list(fontlib._iter_system_fonts()) == []


def test_iter_system_fonts_skips_nonexistent_dir_and_non_ttf_entries(
    monkeypatch, tmp_path
):
    real_dir = tmp_path / "sysfonts"
    real_dir.mkdir()
    (real_dir / "readme.txt").write_text("not a font")
    (real_dir / "Some.ttf").write_text("fake ttf bytes")
    monkeypatch.setattr(
        fontlib, "_SYSTEM_FONT_DIRS", ("/does/not/exist", str(real_dir))
    )
    found = list(fontlib._iter_system_fonts())
    assert [name for name, _, _ in found] == ["Some"]


@requires_system_ttf
def test_available_fonts_dedup_is_case_insensitive_and_user_first(monkeypatch):
    user_dir = tempfile.mkdtemp()
    sys_dir = tempfile.mkdtemp()
    try:
        shutil.copy(SYSTEM_TTF, os.path.join(user_dir, "Dup.ttf"))
        shutil.copy(SYSTEM_TTF, os.path.join(sys_dir, "dup.ttf"))
        monkeypatch.setattr(fontlib, "FONT_DIR", user_dir)
        monkeypatch.setattr(fontlib, "_SYSTEM_FONT_DIRS", (sys_dir,))

        found = fontlib.available_fonts()
        matches = [f for f in found if f["name"].lower() == "dup"]
        assert len(matches) == 1
        assert matches[0]["source"] == "user"
        assert matches[0]["path"] == os.path.join(user_dir, "Dup.ttf")
    finally:
        shutil.rmtree(user_dir, ignore_errors=True)
        shutil.rmtree(sys_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# load_font() / clear_cache()
# ---------------------------------------------------------------------------


def test_load_font_unknown_name_raises(isolated_font_dirs):
    with pytest.raises(fontlib.FontError, match="not found"):
        fontlib.load_font("nope-not-a-font")


def test_load_font_name_lookup_iterates_without_matching(isolated_font_dirs, tmp_path):
    # A non-empty available_fonts() list where no entry matches the
    # requested name - the for-loop must run to completion without ever
    # hitting `break`, distinct from the empty-list case above.
    user_dir = isolated_font_dirs
    font_dir = os.path.join(user_dir, "somebitmap")
    os.makedirs(font_dir)
    _blank_sheet(tmp_path, "s.png")
    shutil.copy(os.path.join(tmp_path, "s.png"), os.path.join(font_dir, "s.png"))
    with open(os.path.join(font_dir, "font.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "name": "somebitmap",
                "sheets": [
                    {
                        "file": "s.png",
                        "cell_w": 4,
                        "cell_h": 4,
                        "ascent": 3,
                        "chars": ["A"],
                    }
                ],
            },
            f,
        )
    with pytest.raises(fontlib.FontError, match="not found"):
        fontlib.load_font("totally-different-name")


def test_load_font_path_like_spec_that_does_not_exist_falls_back_to_name_lookup(
    isolated_font_dirs,
):
    """A spec containing os.sep is first tried as an expanded path; if that
    path doesn't resolve to a bitmap dir or a file, load_font falls through
    to the by-name search (which also fails here) rather than raising a
    different, path-specific error."""
    with pytest.raises(fontlib.FontError, match="not found"):
        fontlib.load_font("/no/such/path/at/all")


def test_load_font_dispatches_bitmap_by_path(tmp_path):
    _blank_sheet(tmp_path, "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "bmp",
            "sheets": [
                {"file": "s.png", "cell_w": 4, "cell_h": 4, "ascent": 3, "chars": ["A"]}
            ],
        },
    )
    font = fontlib.load_font(str(tmp_path))
    assert isinstance(font, fontlib.BitmapFont)


@requires_system_ttf
def test_load_font_dispatches_truetype_by_path():
    font = fontlib.load_font(SYSTEM_TTF)
    assert isinstance(font, fontlib.TrueTypeFont)


@requires_system_ttf
def test_load_font_dispatches_by_name_lookup(isolated_font_dirs):
    user_dir = isolated_font_dirs
    shutil.copy(SYSTEM_TTF, os.path.join(user_dir, "NamedFont.ttf"))
    font = fontlib.load_font("NamedFont")
    assert isinstance(font, fontlib.TrueTypeFont)


def test_load_font_caches_by_spec_string(tmp_path):
    _blank_sheet(tmp_path, "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "bmp",
            "sheets": [
                {"file": "s.png", "cell_w": 4, "cell_h": 4, "ascent": 3, "chars": ["A"]}
            ],
        },
    )
    first = fontlib.load_font(str(tmp_path))
    second = fontlib.load_font(str(tmp_path))
    assert first is second


def test_clear_cache_forces_reload(tmp_path):
    _blank_sheet(tmp_path, "s.png")
    _write_font_json(
        tmp_path,
        {
            "name": "bmp",
            "sheets": [
                {"file": "s.png", "cell_w": 4, "cell_h": 4, "ascent": 3, "chars": ["A"]}
            ],
        },
    )
    first = fontlib.load_font(str(tmp_path))
    fontlib.clear_cache()
    second = fontlib.load_font(str(tmp_path))
    assert first is not second


# ---------------------------------------------------------------------------
# _dilate()
# ---------------------------------------------------------------------------


def test_dilate_zero_passes_is_identity():
    assert fontlib._dilate({(0, 0)}, 0) == {(0, 0)}


def test_dilate_one_pass_grows_right_and_down():
    assert fontlib._dilate({(0, 0)}, 1) == {(0, 0), (1, 0), (0, 1)}


def test_dilate_two_passes_compounds():
    assert fontlib._dilate({(0, 0)}, 2) == {
        (0, 0),
        (1, 0),
        (2, 0),
        (0, 1),
        (1, 1),
        (0, 2),
    }


# ---------------------------------------------------------------------------
# shape()
# ---------------------------------------------------------------------------


def test_shape_rejects_negative_bold(tmp_path):
    font = _simple_bitmap_font(tmp_path)
    with pytest.raises(fontlib.FontError, match="bold must be >= 0"):
        fontlib.shape("A", font, size=1, bold=-1)


def test_shape_rejects_zero_size_for_bitmap_font(tmp_path):
    font = _simple_bitmap_font(tmp_path)
    with pytest.raises(fontlib.FontError, match="scale factor"):
        fontlib.shape("A", font, size=0)


@requires_system_ttf
def test_shape_rejects_zero_size_for_truetype_font():
    font = fontlib.TrueTypeFont(SYSTEM_TTF)
    with pytest.raises(fontlib.FontError, match="pixel height"):
        fontlib.shape("A", font, size=0)


@requires_system_ttf
def test_shape_truetype_font_success():
    font = fontlib.TrueTypeFont(SYSTEM_TTF)
    ink, metrics = fontlib.shape("A", font, size=12)
    assert ink
    assert metrics["width"] > 0
    assert metrics["height"] > 0


def test_shape_empty_ink_returns_zeroed_metrics(tmp_path):
    """Every character unmapped -> no ink -> the early-return metrics branch,
    which (unlike the non-empty branch) reports advance_width without the
    `+ bold` term."""
    font = _simple_bitmap_font(tmp_path, chars="A")
    ink, metrics = fontlib.shape("ZZZ", font, size=1)
    assert ink == set()
    assert metrics == {
        "advance_width": 0,
        "width": 0,
        "height": 0,
        "left": 0,
        "top": 0,
        "bottom": 0,
    }


def test_shape_bold_adds_dilation_and_widens_advance(tmp_path):
    font = _simple_bitmap_font(tmp_path, chars="A")
    plain_ink, plain_metrics = fontlib.shape("A", font, size=2)
    bold_ink, bold_metrics = fontlib.shape("A", font, size=2, bold=1)
    assert bold_ink >= plain_ink
    assert bold_ink != plain_ink
    assert bold_metrics["advance_width"] == plain_metrics["advance_width"] + 1


def test_shape_metrics_bounding_box(tmp_path):
    font = _simple_bitmap_font(tmp_path, chars="A")
    ink, metrics = fontlib.shape("A", font, size=1)
    xs = [x for x, _ in ink]
    ys = [y for _, y in ink]
    assert metrics["left"] == min(xs)
    assert metrics["top"] == min(ys)
    assert metrics["bottom"] == max(ys)
    assert metrics["width"] == max(xs) - min(xs) + 1
    assert metrics["height"] == max(ys) - min(ys) + 1
