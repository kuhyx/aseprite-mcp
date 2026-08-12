"""Coverage gaps in pixel_read.py not hit by test_composite_read.py or
test_error_propagation.py: validation guards, successful get_pixels_rect,
and out-of-range frame indices.

Note: pixel_read.py uses the raw (unchecked) execute_lua_script and handles
"ERROR:" lines itself, so its `if not success:` branches (the ones for a
process-level failure, as opposed to an in-script ERROR: line) require
Aseprite to exit non-zero. A garbage/corrupt .aseprite file does NOT do
that: Aseprite prints "Error reading header" to stderr but still exits 0
with no active sprite, which is caught by the script's own "ERROR:No
active sprite" line instead. Confirmed by direct probe (see task report);
those `if not success:` branches are covered below via mocking
AsepriteCommand.execute_lua_script directly, the same pattern used for
core/commands.py's subprocess boundary.
"""

import json
from unittest.mock import patch

from conftest import ok, run

from aseprite_mcp.tools import pixel_read

# --- get_pixel_color ---


def test_get_pixel_color_missing_file():
    result = run(pixel_read.get_pixel_color("/tmp/ase-pytest/nope.aseprite", 0, 0))
    assert "not found" in result


# --- get_pixels_rect ---


def test_get_pixels_rect_missing_file():
    result = run(
        pixel_read.get_pixels_rect("/tmp/ase-pytest/nope.aseprite", 0, 0, 4, 4)
    )
    assert "not found" in result


def test_get_pixels_rect_bad_dims(sprite):
    result = run(pixel_read.get_pixels_rect(sprite, 0, 0, 0, 4))
    assert "must be > 0" in result


def test_get_pixels_rect_success(sprite):
    # fixture: 32x32, 'body' layer, red rect at (8,8,16,16).
    px = json.loads(ok(run(pixel_read.get_pixels_rect(sprite, 8, 8, 4, 4, "body", 1))))
    assert len(px) == 16
    assert all(p["hex"].lower() == "#d04648" for p in px)


# --- get_composite_pixel ---


def test_get_composite_pixel_missing_file():
    result = run(pixel_read.get_composite_pixel("/tmp/ase-pytest/nope.aseprite", 0, 0))
    assert "not found" in result


def test_get_composite_pixel_frame_out_of_range(sprite):
    result = run(pixel_read.get_composite_pixel(sprite, 0, 0, 99))
    assert str(result).startswith(("Failed", "ERROR"))


# --- get_composite_rect ---


def test_get_composite_rect_missing_file():
    result = run(
        pixel_read.get_composite_rect("/tmp/ase-pytest/nope.aseprite", 0, 0, 4, 4)
    )
    assert "not found" in result


def test_get_composite_rect_bad_dims(sprite):
    result = run(pixel_read.get_composite_rect(sprite, 0, 0, 4, 0))
    assert "must be > 0" in result


def test_get_composite_rect_frame_out_of_range(sprite):
    result = run(pixel_read.get_composite_rect(sprite, 0, 0, 2, 2, 99))
    assert str(result).startswith(("Failed", "ERROR"))


# --- mocked execute_lua_script: process-level (not in-script) failures ---


def test_get_pixel_color_reports_subprocess_failure(sprite):
    with patch("aseprite_mcp.tools.pixel_read.AsepriteCommand.execute_lua_script") as m:
        m.return_value = (False, "boom")
        result = run(pixel_read.get_pixel_color(sprite, 0, 0))
    assert result == "Failed to read pixel: boom"


def test_get_pixels_rect_reports_subprocess_failure(sprite):
    with patch("aseprite_mcp.tools.pixel_read.AsepriteCommand.execute_lua_script") as m:
        m.return_value = (False, "boom")
        result = run(pixel_read.get_pixels_rect(sprite, 0, 0, 2, 2))
    assert result == "Failed to read pixels: boom"


def test_get_composite_pixel_reports_subprocess_failure(sprite):
    with patch("aseprite_mcp.tools.pixel_read.AsepriteCommand.execute_lua_script") as m:
        m.return_value = (False, "boom")
        result = run(pixel_read.get_composite_pixel(sprite, 0, 0))
    assert result == "Failed to read composite pixel: boom"


def test_get_composite_rect_reports_subprocess_failure(sprite):
    with patch("aseprite_mcp.tools.pixel_read.AsepriteCommand.execute_lua_script") as m:
        m.return_value = (False, "boom")
        result = run(pixel_read.get_composite_rect(sprite, 0, 0, 2, 2))
    assert result == "Failed to read composite pixels: boom"


def test_get_pixel_color_no_pixel_data_returned(sprite):
    with patch("aseprite_mcp.tools.pixel_read.AsepriteCommand.execute_lua_script") as m:
        m.return_value = (True, "nothing useful here")
        result = run(pixel_read.get_pixel_color(sprite, 0, 0))
    assert result == "No pixel data returned"


def test_get_pixels_rect_no_pixel_data_returned(sprite):
    with patch("aseprite_mcp.tools.pixel_read.AsepriteCommand.execute_lua_script") as m:
        m.return_value = (True, "nothing useful here")
        result = run(pixel_read.get_pixels_rect(sprite, 0, 0, 2, 2))
    assert result == "No pixel data returned"


def test_get_composite_pixel_no_pixel_data_returned(sprite):
    with patch("aseprite_mcp.tools.pixel_read.AsepriteCommand.execute_lua_script") as m:
        m.return_value = (True, "nothing useful here")
        result = run(pixel_read.get_composite_pixel(sprite, 0, 0))
    assert result == "No pixel data returned"


def test_get_composite_rect_no_pixel_data_returned(sprite):
    with patch("aseprite_mcp.tools.pixel_read.AsepriteCommand.execute_lua_script") as m:
        m.return_value = (True, "nothing useful here")
        result = run(pixel_read.get_composite_rect(sprite, 0, 0, 2, 2))
    assert result == "No pixel data returned"
