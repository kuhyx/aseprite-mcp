"""Coverage gaps in transform.py: rotate_layer, resize_canvas, crop_canvas
success paths and validation guards not hit by test_error_propagation.py.

Uses its own function-scoped sprites (never the module-scoped `sprite`
fixture) because resize/crop/rotate mutate the file in place and would
corrupt state for any other test sharing it.
"""

import json
import os

import pytest
from conftest import BASE, ok, run

from aseprite_mcp.tools import analysis, animation, canvas, drawing, transform

CORRUPT = f"{BASE}/transform_corrupt.aseprite"


def _make_corrupt():
    os.makedirs(BASE, exist_ok=True)
    if not os.path.exists(CORRUPT):
        with open(CORRUPT, "w") as f:
            f.write("this is not a real aseprite file")
    return CORRUPT


@pytest.fixture
def fresh(base_dir, request):
    """A small non-square sprite with an asymmetric painted layer.

    Non-square (12x6) so 90/270 degree rotation swaps width/height in a
    way that would be wrong if the axes were mixed up.
    """
    path = f"{BASE}/transform_{request.node.name}.aseprite"
    ok(run(canvas.create_canvas(12, 6, path)))
    ok(run(canvas.add_layer(path, "body")))
    ok(run(drawing.draw_rectangle_at(path, "body", 1, 0, 0, 4, 2, "#D04648", True)))
    return path


def _opaque_count(path, frame=1):
    stats = json.loads(run(analysis.get_color_stats(path, frame)))
    return stats["opaque_pixels"]


# --- flip_layer ---


def test_flip_layer_missing_file():
    result = run(transform.flip_layer("/tmp/ase-pytest/nope_flip.aseprite", "body", 1))
    assert "not found" in result


def test_flip_layer_bad_direction(fresh):
    result = run(transform.flip_layer(fresh, "body", 1, "diagonal"))
    assert "direction must be" in result


def test_flip_layer_horizontal_success(fresh):
    before = _opaque_count(fresh)
    ok(run(transform.flip_layer(fresh, "body", 1, "horizontal")))
    assert _opaque_count(fresh) == before


def test_flip_layer_vertical_success(fresh):
    before = _opaque_count(fresh)
    ok(run(transform.flip_layer(fresh, "body", 1, "vertical")))
    assert _opaque_count(fresh) == before


# --- rotate_layer ---


def test_rotate_layer_missing_file():
    result = run(
        transform.rotate_layer("/tmp/ase-pytest/nope_rotate.aseprite", "body", 1)
    )
    assert "not found" in result


def test_rotate_layer_bad_angle(fresh):
    result = run(transform.rotate_layer(fresh, "body", 1, 45))
    assert "angle must be" in result


def test_rotate_layer_missing_layer(fresh):
    result = run(transform.rotate_layer(fresh, "NO_SUCH_LAYER", 1, 90))
    assert str(result).startswith(("Failed", "ERROR"))


def test_rotate_layer_90_success(fresh):
    before = _opaque_count(fresh)
    ok(run(transform.rotate_layer(fresh, "body", 1, 90)))
    assert _opaque_count(fresh) == before


def test_rotate_layer_180_success(fresh):
    before = _opaque_count(fresh)
    ok(run(transform.rotate_layer(fresh, "body", 1, 180)))
    assert _opaque_count(fresh) == before


def test_rotate_layer_270_success(fresh):
    before = _opaque_count(fresh)
    ok(run(transform.rotate_layer(fresh, "body", 1, 270)))
    assert _opaque_count(fresh) == before


# --- resize_canvas ---


def test_resize_canvas_missing_file():
    result = run(transform.resize_canvas("/tmp/ase-pytest/nope_resize.aseprite", 8, 8))
    assert "not found" in result


def test_resize_canvas_bad_dims(fresh):
    result = run(transform.resize_canvas(fresh, 0, 8))
    assert "must be > 0" in result


def test_resize_canvas_success(fresh):
    ok(run(transform.resize_canvas(fresh, 24, 12)))
    info = json.loads(run(animation.get_sprite_info(fresh)))
    assert info["width"] == 24
    assert info["height"] == 12


def test_resize_canvas_corrupt_file():
    # A garbage file exists but Aseprite can't open it as a sprite, so the
    # script's own "ERROR:No active sprite" line flips
    # execute_lua_script_checked's success flag to False.
    result = run(transform.resize_canvas(_make_corrupt(), 8, 8))
    assert result == "Failed to resize canvas: No active sprite"


# --- crop_canvas ---


def test_crop_canvas_missing_file():
    result = run(
        transform.crop_canvas("/tmp/ase-pytest/nope_crop.aseprite", 0, 0, 4, 4)
    )
    assert "not found" in result


def test_crop_canvas_bad_dims(fresh):
    result = run(transform.crop_canvas(fresh, 0, 0, 4, 0))
    assert "must be > 0" in result


def test_crop_canvas_success(fresh):
    ok(run(transform.crop_canvas(fresh, 0, 0, 4, 2)))
    info = json.loads(run(animation.get_sprite_info(fresh)))
    assert info["width"] == 4
    assert info["height"] == 2
