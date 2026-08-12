"""Tilemap tools (tilemap.py)."""

import json
from unittest.mock import patch

from conftest import ok, run

from aseprite_mcp.tools import tilemap


def test_create_tilemap_layer(sprite):
    ok(run(tilemap.create_tilemap_layer(sprite, "terrain", 8, 8)))


def test_draw_on_tiles(sprite):
    ok(
        run(
            tilemap.draw_on_tile(
                sprite,
                "terrain",
                1,
                [
                    {"x": x, "y": y, "color": "#3E8948"}
                    for x in range(8)
                    for y in range(8)
                ],
            )
        )
    )
    ok(
        run(
            tilemap.draw_on_tile(
                sprite,
                "terrain",
                2,
                [
                    {"x": x, "y": y, "color": "#743F39"}
                    for x in range(8)
                    for y in range(4)
                ],
            )
        )
    )


def test_get_tilemap_info(sprite):
    info = json.loads(ok(run(tilemap.get_tilemap_info(sprite, "terrain"))))
    assert info == {
        "tile_width": 8,
        "tile_height": 8,
        "tile_count": 2,
        "map_cols": 4,
        "map_rows": 4,
    }


def test_set_and_get_tiles(sprite):
    ok(
        run(
            tilemap.set_tiles(
                sprite,
                "terrain",
                1,
                [
                    {"col": 0, "row": 3, "tile_index": 1},
                    {"col": 1, "row": 3, "tile_index": 1},
                    {"col": 2, "row": 3, "tile_index": 2},
                    {"col": 3, "row": 3, "tile_index": 1},
                ],
            )
        )
    )
    tile = json.loads(ok(run(tilemap.get_tile_at(sprite, "terrain", 1, 2, 3))))
    assert tile["tile_index"] == 2


def test_set_tiles_rejects_out_of_range_index(sprite):
    result = run(
        tilemap.set_tiles(
            sprite, "terrain", 1, [{"col": 0, "row": 0, "tile_index": 99}]
        )
    )
    assert "out of range" in result


# ── _parse_hex_color branches (exercised via draw_on_tile) ──────────────


def test_draw_on_tile_rejects_empty_color(sprite):
    result = run(
        tilemap.draw_on_tile(sprite, "terrain", 1, [{"x": 0, "y": 0, "color": ""}])
    )
    assert result == "Invalid color value: "


def test_draw_on_tile_rejects_wrong_length_color(sprite):
    result = run(
        tilemap.draw_on_tile(sprite, "terrain", 1, [{"x": 0, "y": 0, "color": "#FFF"}])
    )
    assert "Invalid color value" in result


def test_draw_on_tile_rejects_non_hex_color(sprite):
    result = run(
        tilemap.draw_on_tile(
            sprite, "terrain", 1, [{"x": 0, "y": 0, "color": "#ZZZZZZ"}]
        )
    )
    assert "Invalid color value" in result


# ── file-not-found guards ───────────────────────────────────────────────

MISSING = "/tmp/ase-pytest/does-not-exist.aseprite"


def test_create_tilemap_layer_missing_file():
    result = run(tilemap.create_tilemap_layer(MISSING, "terrain", 8, 8))
    assert result == f"File {MISSING} not found"


def test_draw_on_tile_missing_file():
    result = run(
        tilemap.draw_on_tile(
            MISSING, "terrain", 1, [{"x": 0, "y": 0, "color": "#FFFFFF"}]
        )
    )
    assert result == f"File {MISSING} not found"


def test_set_tiles_missing_file():
    result = run(
        tilemap.set_tiles(
            MISSING, "terrain", 1, [{"col": 0, "row": 0, "tile_index": 0}]
        )
    )
    assert result == f"File {MISSING} not found"


def test_get_tile_at_missing_file():
    result = run(tilemap.get_tile_at(MISSING, "terrain", 1, 0, 0))
    assert result == f"File {MISSING} not found"


def test_get_tilemap_info_missing_file():
    result = run(tilemap.get_tilemap_info(MISSING, "terrain"))
    assert result == f"File {MISSING} not found"


# ── validation branches ─────────────────────────────────────────────────


def test_create_tilemap_layer_rejects_non_positive_dimensions(sprite):
    result = run(tilemap.create_tilemap_layer(sprite, "bad-tiles", 0, 8))
    assert result == "Tile dimensions must be > 0"
    result = run(tilemap.create_tilemap_layer(sprite, "bad-tiles", 8, -1))
    assert result == "Tile dimensions must be > 0"


def test_create_tilemap_layer_rejects_duplicate_name(sprite):
    result = run(tilemap.create_tilemap_layer(sprite, "terrain", 8, 8))
    assert result.startswith("Failed to create tilemap layer:")
    assert "already exists" in result


def test_draw_on_tile_rejects_tile_index_below_one(sprite):
    result = run(
        tilemap.draw_on_tile(
            sprite, "terrain", 0, [{"x": 0, "y": 0, "color": "#FFFFFF"}]
        )
    )
    assert "tile_index must be >= 1" in result


def test_draw_on_tile_rejects_empty_pixels(sprite):
    result = run(tilemap.draw_on_tile(sprite, "terrain", 1, []))
    assert result == "Pixels list cannot be empty"


def test_set_tiles_rejects_empty_tiles(sprite):
    result = run(tilemap.set_tiles(sprite, "terrain", 1, []))
    assert result == "Tiles list cannot be empty"


# ── "Failed to X" script-error branches ─────────────────────────────────


def test_draw_on_tile_reports_layer_not_found(sprite):
    result = run(
        tilemap.draw_on_tile(
            sprite, "no-such-layer", 1, [{"x": 0, "y": 0, "color": "#FFFFFF"}]
        )
    )
    assert result.startswith("Failed to draw on tile:")


def test_draw_on_tile_reports_not_a_tilemap_layer(sprite):
    result = run(
        tilemap.draw_on_tile(sprite, "body", 1, [{"x": 0, "y": 0, "color": "#FFFFFF"}])
    )
    assert result.startswith("Failed to draw on tile:")
    assert "not a tilemap layer" in result


def test_draw_on_tile_reports_index_out_of_range(sprite):
    result = run(
        tilemap.draw_on_tile(
            sprite, "terrain", 999, [{"x": 0, "y": 0, "color": "#FFFFFF"}]
        )
    )
    assert result.startswith("Failed to draw on tile:")
    assert "out of range" in result


def test_draw_on_tile_appends_new_tile_at_current_count(sprite):
    info = json.loads(ok(run(tilemap.get_tilemap_info(sprite, "terrain"))))
    next_index = info["tile_count"] + 1
    result = ok(
        run(
            tilemap.draw_on_tile(
                sprite, "terrain", next_index, [{"x": 0, "y": 0, "color": "#123456"}]
            )
        )
    )
    assert f"tile {next_index}" in result


def test_set_tiles_reports_layer_not_found(sprite):
    result = run(
        tilemap.set_tiles(
            sprite, "no-such-layer", 1, [{"col": 0, "row": 0, "tile_index": 0}]
        )
    )
    assert result.startswith("Failed to set tiles:")


def test_set_tiles_reports_frame_out_of_range(sprite):
    result = run(
        tilemap.set_tiles(
            sprite, "terrain", 999, [{"col": 0, "row": 0, "tile_index": 0}]
        )
    )
    assert result.startswith("Failed to set tiles:")
    assert "out of range" in result


def test_set_tiles_reports_not_a_tilemap_layer(sprite):
    result = run(
        tilemap.set_tiles(sprite, "body", 1, [{"col": 0, "row": 0, "tile_index": 0}])
    )
    assert result.startswith("Failed to set tiles:")
    assert "not a tilemap layer" in result


def test_set_tiles_reports_position_outside_map(sprite):
    result = run(
        tilemap.set_tiles(
            sprite, "terrain", 1, [{"col": 99, "row": 99, "tile_index": 0}]
        )
    )
    assert result.startswith("Failed to set tiles:")
    assert "outside the" in result


def test_get_tile_at_reports_layer_not_found(sprite):
    result = run(tilemap.get_tile_at(sprite, "no-such-layer", 1, 0, 0))
    assert result.startswith("Failed to read tile:")


def test_get_tile_at_reports_frame_out_of_range(sprite):
    result = run(tilemap.get_tile_at(sprite, "terrain", 999, 0, 0))
    assert result.startswith("Failed to read tile:")
    assert "out of range" in result


def test_get_tile_at_reports_not_a_tilemap_layer(sprite):
    result = run(tilemap.get_tile_at(sprite, "body", 1, 0, 0))
    assert result.startswith("Failed to read tile:")
    assert "not a tilemap layer" in result


def test_get_tile_at_outside_cel_bounds_returns_zero(sprite):
    # A grid cell far outside where any cel data exists should read as the
    # empty tile (0) rather than erroring.
    tile = json.loads(ok(run(tilemap.get_tile_at(sprite, "terrain", 1, 3, 0))))
    assert tile["tile_index"] == 0


def test_get_tilemap_info_reports_layer_not_found(sprite):
    result = run(tilemap.get_tilemap_info(sprite, "no-such-layer"))
    assert result.startswith("Failed to get tilemap info:")


def test_get_tilemap_info_reports_not_a_tilemap_layer(sprite):
    result = run(tilemap.get_tilemap_info(sprite, "body"))
    assert result.startswith("Failed to get tilemap info:")
    assert "not a tilemap layer" in result


def test_get_tile_at_skips_non_tile_lines_before_matching(sprite):
    with patch(
        "aseprite_mcp.tools.tilemap.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "some noise\nTILE:5")
        result = run(tilemap.get_tile_at(sprite, "body", 1, 0, 0))
    assert json.loads(result)["tile_index"] == 5


def test_get_tile_at_no_tile_data_returned(sprite):
    with patch(
        "aseprite_mcp.tools.tilemap.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "nothing useful here")
        result = run(tilemap.get_tile_at(sprite, "body", 1, 0, 0))
    assert result == "No tile data returned"


def test_get_tilemap_info_skips_non_info_lines_before_matching(sprite):
    with patch(
        "aseprite_mcp.tools.tilemap.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "some noise\nINFO:8,8,4,2,2")
        result = run(tilemap.get_tilemap_info(sprite, "body"))
    assert json.loads(result)["tile_width"] == 8


def test_get_tilemap_info_no_data_returned(sprite):
    with patch(
        "aseprite_mcp.tools.tilemap.AsepriteCommand.execute_lua_script_checked"
    ) as m:
        m.return_value = (True, "nothing useful here")
        result = run(tilemap.get_tilemap_info(sprite, "body"))
    assert result == "No tilemap data returned"
