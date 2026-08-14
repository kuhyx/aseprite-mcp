"""Regression tests for issue #15: Lua-side errors must reach the caller.

Before the fix, `aseprite --batch --script` discarded the script's Lua
`return` value and always exited 0, so mutating tools fabricated a success
message from their input args even when the script did nothing. Every call
below feeds invalid input and asserts the tool now reports failure instead
of a fabricated success.
"""

from conftest import ok, run

from aseprite_mcp.tools import (
    animation,
    canvas,
    drawing,
    export,
    palette,
    pixel_read,
    quality,
    scene,
    transform,
)


def failed(result: object) -> object:
    """Assert a tool surfaced a failure rather than a fabricated success."""
    assert str(result).startswith(("Failed", "ERROR")), result
    return result


# --- issue #15 reproduction table: each must now fail loudly ---


def test_set_layer_visibility_missing_layer(sprite: str) -> None:
    failed(run(animation.set_layer_visibility(sprite, "NOT_A_LAYER", visible=False)))


def test_set_frame_duration_out_of_range(sprite: str) -> None:
    failed(run(canvas.set_frame_duration(sprite, 99, 50)))


def test_set_tag_range_out_of_bounds(sprite: str) -> None:
    failed(run(animation.set_tag(sprite, "bad_tag", 5, 99)))


def test_remap_colors_missing_layer(sprite: str) -> None:
    failed(
        run(
            palette.remap_colors_in_cel_range(
                sprite, "NOSUCHLAYER", 1, 1, [{"from": "#D04648", "to": "#000000"}]
            )
        )
    )


def test_ensure_layers_present_all_missing(sprite: str) -> None:
    failed(run(quality.ensure_layers_present(sprite, ["MISSING"])))


def test_export_sprite_unwritable_format(sprite: str) -> None:
    # Aseprite exits 0 but writes nothing for output_format="json".
    failed(run(export.export_sprite(sprite, "/tmp/ase-pytest/err_out", "json")))


def test_export_tag_missing_tag(sprite: str) -> None:
    # --tag silently exports *all* frames (exit 0) for an unknown tag, so the
    # tool must validate the tag rather than report a fabricated tag export.
    failed(run(export.export_tag(sprite, "NO_SUCH_TAG", "/tmp/ase-pytest/err_tag.gif")))


def test_export_spritesheet_missing_tag(sprite: str) -> None:
    failed(
        run(
            export.export_spritesheet(
                sprite,
                "/tmp/ase-pytest/err_sheet.png",
                "horizontal",
                "",
                1,
                0,
                "NO_SUCH_TAG",
            )
        )
    )


# --- readers surfaced a hard error as data (read as success); now fail loudly ---


def test_get_pixel_color_missing_layer(sprite: str) -> None:
    failed(run(pixel_read.get_pixel_color(sprite, 0, 0, "NO_SUCH_LAYER")))


def test_get_pixels_rect_missing_layer(sprite: str) -> None:
    failed(run(pixel_read.get_pixels_rect(sprite, 0, 0, 4, 4, "NO_SUCH_LAYER")))


# --- copy_layers_between_sprites: all-missing fails; partial surfaces skips ---


def test_copy_layers_all_missing_fails(sprite: str, base_dir: str) -> None:
    target = f"{base_dir}/copy_target.aseprite"
    ok(run(canvas.create_canvas(16, 16, target)))
    failed(run(scene.copy_layers_between_sprites(sprite, target, ["BOGUS"])))


def test_copy_layers_partial_surfaces_skipped(sprite: str, base_dir: str) -> None:
    target = f"{base_dir}/copy_target2.aseprite"
    ok(run(canvas.create_canvas(16, 16, target)))
    result = run(scene.copy_layers_between_sprites(sprite, target, ["body", "BOGUS"]))
    ok(result)
    assert "skipped missing layers" in result, result
    assert "BOGUS" in result, result


# --- new guards added alongside the conversion ---


def test_crop_fully_outside_canvas_rejected(sprite: str) -> None:
    failed(run(transform.crop_canvas(sprite, 999, 999, 10, 10)))


def test_flip_missing_layer(sprite: str) -> None:
    failed(run(transform.flip_layer(sprite, "NO_SUCH_LAYER", 1)))


def test_draw_line_missing_layer(sprite: str) -> None:
    failed(
        run(drawing.draw_line_at(sprite, "NO_SUCH_LAYER", 1, 0, 0, 5, 5, "#ffffff", 1))
    )
