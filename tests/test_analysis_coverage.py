"""Coverage gaps in analysis.py not hit by test_analysis.py: validation
guards on render_onion_skin/get_color_stats and out-of-range frame indices
on compare_frames/get_color_stats.
"""

import os

import pytest

from conftest import BASE, ok, run

from aseprite_mcp.tools import analysis


# --- render_onion_skin ---


def test_render_onion_skin_missing_file():
    result = run(
        analysis.render_onion_skin(
            "/tmp/ase-pytest/nope.aseprite", 1, f"{BASE}/onion_missing.png"
        )
    )
    assert "not found" in result


def test_render_onion_skin_bad_scale(sprite):
    result = run(
        analysis.render_onion_skin(sprite, 1, f"{BASE}/onion_bad_scale.png", scale=0)
    )
    assert "scale must be" in result


def test_render_onion_skin_bad_ghost_opacity(sprite):
    result = run(
        analysis.render_onion_skin(
            sprite, 1, f"{BASE}/onion_bad_opacity.png", ghost_opacity=999
        )
    )
    assert "ghost_opacity must be" in result


def test_render_onion_skin_bad_before_after(sprite):
    result = run(
        analysis.render_onion_skin(sprite, 1, f"{BASE}/onion_bad_before.png", before=-1)
    )
    assert "before and after must be" in result


def test_render_onion_skin_rejects_traversal(sprite):
    # os.path.normpath collapses "BASE/../x" before reject_traversal's check
    # ever sees a ".." component, so an absolute path can't trigger the
    # guard. A relative path that walks above cwd survives normpath instead.
    # Skip (rather than assert) if this pytest run's cwd doesn't produce one,
    # so the test is cwd-robust instead of cwd-asserting.
    traversal_path = os.path.relpath(f"{BASE}/evil_onion.png")
    if ".." not in traversal_path.split(os.sep):
        pytest.skip(f"cwd {os.getcwd()!r} yields no '..' in relpath")
    result = run(analysis.render_onion_skin(sprite, 1, traversal_path))
    assert "Invalid" in result


def test_render_onion_skin_appends_png_extension(sprite):
    out = f"{BASE}/onion_noext"
    result = ok(run(analysis.render_onion_skin(sprite, 1, out)))
    assert out + ".png" in result
    assert os.path.exists(out + ".png")


def test_render_onion_skin_frame_out_of_range(sprite):
    result = run(analysis.render_onion_skin(sprite, 99, f"{BASE}/onion_oor.png"))
    assert result == "Failed to render onion skin: Frame index out of range"


# --- compare_frames ---


def test_compare_frames_missing_file():
    result = run(analysis.compare_frames("/tmp/ase-pytest/nope.aseprite", 1, 1))
    assert "not found" in result


def test_compare_frames_out_of_range(sprite):
    result = run(analysis.compare_frames(sprite, 1, 99))
    assert str(result).startswith(("Failed", "ERROR"))


# --- get_color_stats ---


def test_get_color_stats_missing_file():
    result = run(analysis.get_color_stats("/tmp/ase-pytest/nope.aseprite"))
    assert "not found" in result


def test_get_color_stats_bad_top(sprite):
    result = run(analysis.get_color_stats(sprite, 1, top=0))
    assert "top must be" in result


def test_get_color_stats_frame_out_of_range(sprite):
    result = run(analysis.get_color_stats(sprite, 99))
    assert str(result).startswith(("Failed", "ERROR"))
