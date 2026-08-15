"""Coverage gaps in analysis.py not hit by test_analysis.py.

Covers validation guards on render_onion_skin/get_color_stats and
out-of-range frame indices on compare_frames/get_color_stats.
"""

from pathlib import Path
from unittest.mock import patch

from conftest import BASE, ok, run

from aseprite_mcp.tools import analysis

# --- render_onion_skin ---


def test_render_onion_skin_missing_file() -> None:
    result = run(
        analysis.render_onion_skin(
            "/tmp/ase-pytest/nope.aseprite", 1, f"{BASE}/onion_missing.png"
        )
    )
    assert "not found" in result


def test_render_onion_skin_bad_scale(sprite: str) -> None:
    result = run(
        analysis.render_onion_skin(sprite, 1, f"{BASE}/onion_bad_scale.png", scale=0)
    )
    assert "scale must be" in result


def test_render_onion_skin_bad_ghost_opacity(sprite: str) -> None:
    result = run(
        analysis.render_onion_skin(
            sprite, 1, f"{BASE}/onion_bad_opacity.png", ghost_opacity=999
        )
    )
    assert "ghost_opacity must be" in result


def test_render_onion_skin_bad_before_after(sprite: str) -> None:
    result = run(
        analysis.render_onion_skin(sprite, 1, f"{BASE}/onion_bad_before.png", before=-1)
    )
    assert "before and after must be" in result


def test_render_onion_skin_rejects_traversal(sprite: str) -> None:
    # reject_traversal now checks raw components, so a mid-path ".." is
    # caught whether or not normalization would cancel it out. This used to
    # need a cwd-dependent relpath (and a skip when the cwd produced none)
    # because only traversal surviving normpath was rejected.
    result = run(analysis.render_onion_skin(sprite, 1, f"{BASE}/../evil_onion.png"))
    assert "Invalid" in result


def test_render_onion_skin_appends_png_extension(sprite: str) -> None:
    out = f"{BASE}/onion_noext"
    result = ok(run(analysis.render_onion_skin(sprite, 1, out)))
    assert out + ".png" in result
    assert Path(out + ".png").exists()


def test_render_onion_skin_frame_out_of_range(sprite: str) -> None:
    result = run(analysis.render_onion_skin(sprite, 99, f"{BASE}/onion_oor.png"))
    assert result == "Failed to render onion skin: Frame index out of range"


# --- compare_frames ---


def test_compare_frames_missing_file() -> None:
    result = run(analysis.compare_frames("/tmp/ase-pytest/nope.aseprite", 1, 1))
    assert "not found" in result


def test_compare_frames_out_of_range(sprite: str) -> None:
    result = run(analysis.compare_frames(sprite, 1, 99))
    assert str(result).startswith(("Failed", "ERROR"))


def test_compare_frames_skips_non_diff_lines_before_matching(sprite: str) -> None:
    # Forces the `for line in output.splitlines()` loop past a non-"DIFF:"
    # line before finding the real one, exercising the loop-continue arc.
    with patch(
        "aseprite_mcp.tools.analysis.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "some noise\nDIFF:5,1024,0,0,3,3,1")
        result = run(analysis.compare_frames(sprite, 1, 2))
    assert '"changed_pixels": 5' in result


def test_compare_frames_no_diff_data_returned(sprite: str) -> None:
    with patch(
        "aseprite_mcp.tools.analysis.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "nothing useful here")
        result = run(analysis.compare_frames(sprite, 1, 2))
    assert result == "No diff data returned"


# --- get_color_stats ---


def test_get_color_stats_missing_file() -> None:
    result = run(analysis.get_color_stats("/tmp/ase-pytest/nope.aseprite"))
    assert "not found" in result


def test_get_color_stats_bad_top(sprite: str) -> None:
    result = run(analysis.get_color_stats(sprite, 1, top=0))
    assert "top must be" in result


def test_get_color_stats_frame_out_of_range(sprite: str) -> None:
    result = run(analysis.get_color_stats(sprite, 99))
    assert str(result).startswith(("Failed", "ERROR"))


def test_get_color_stats_skips_non_matching_lines_before_matching(sprite: str) -> None:
    # Forces the parsing loop past a line that matches none of the
    # COLOR:/OPAQUE:/UNIQUE: prefixes, exercising the loop-continue arc.
    with patch(
        "aseprite_mcp.tools.analysis.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (
            True,
            "some noise\nCOLOR:#ff0000,10\nOPAQUE:10\nUNIQUE:1",
        )
        result = run(analysis.get_color_stats(sprite))
    assert '"unique_colors": 1' in result
