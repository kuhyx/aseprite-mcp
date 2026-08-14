"""B3 (cel-normalization, no silent clip) + B4 (per-pixel alpha) fixes."""

from conftest import ok, run

from aseprite_mcp.tools import canvas, drawing, pixel_read


def _rgba(pixel_result: str) -> tuple[int, int, int, int]:
    s = str(pixel_result)
    return (
        int(s.split("r=")[1].split(",", maxsplit=1)[0]),
        int(s.split("g=")[1].split(",", maxsplit=1)[0]),
        int(s.split("b=")[1].split(",", maxsplit=1)[0]),
        int(s.split("a=")[1].split(")", maxsplit=1)[0]),
    )


def test_polygon_offcanvas_vertices_no_clip(sprite: str) -> None:
    # Two vertices are outside the 32x32 canvas; pset() must bounds-guard
    # (no crash) and the in-canvas fill must still land at sprite-global (16,16).
    ok(run(canvas.add_layer(sprite, "poly")))
    pts = [{"x": 16, "y": -5}, {"x": -5, "y": 30}, {"x": 30, "y": 30}]
    ok(
        run(
            drawing.draw_polygon(
                sprite, "poly", 1, pts, "#00FF00", fill=True, create_if_missing=True
            )
        )
    )
    r, g, b, _ = _rgba(run(pixel_read.get_pixel_color(sprite, 16, 16, "poly", 1)))
    assert (r, g, b) == (0, 255, 0), (r, g, b)


def test_gradient_lands_at_sprite_global(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "grad")))
    ok(
        run(
            drawing.apply_gradient_rect(
                sprite,
                "grad",
                1,
                4,
                4,
                16,
                1,
                "#000000",
                "#FFFFFF",
                horizontal=True,
                create_if_missing=True,
            )
        )
    )
    left = _rgba(run(pixel_read.get_pixel_color(sprite, 4, 4, "grad", 1)))
    right = _rgba(run(pixel_read.get_pixel_color(sprite, 19, 4, "grad", 1)))
    assert left[0] < right[0], (left, right)  # dark -> light, left to right


def test_draw_accepts_rgba_alpha(sprite: str) -> None:
    # "#RRGGBBAA" was rejected before B4 (len != 6) and left the layer empty.
    ok(run(canvas.add_layer(sprite, "alpha")))
    ok(
        run(
            drawing.draw_pixels_at(
                sprite,
                "alpha",
                1,
                [{"x": 6, "y": 6, "color": "#FF000080"}],
                create_if_missing=True,
            )
        )
    )
    r, g, b, a = _rgba(run(pixel_read.get_pixel_color(sprite, 6, 6, "alpha", 1)))
    assert (r, g, b) == (255, 0, 0)
    assert a == 0x80  # semi-transparency preserved


def test_draw_accepts_short_hex(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "short")))
    ok(
        run(
            drawing.draw_pixels_at(
                sprite,
                "short",
                1,
                [{"x": 5, "y": 5, "color": "#0F0"}],
                create_if_missing=True,
            )
        )
    )
    assert _rgba(run(pixel_read.get_pixel_color(sprite, 5, 5, "short", 1))) == (
        0,
        255,
        0,
        255,
    )


def test_draw_rejects_bad_hex(sprite: str) -> None:
    ok(run(canvas.add_layer(sprite, "bad")))
    res = run(
        drawing.draw_pixels_at(
            sprite,
            "bad",
            1,
            [{"x": 0, "y": 0, "color": "#GG0000"}],
            create_if_missing=True,
        )
    )
    assert res.startswith(("Invalid", "Failed"))


def test_draw_pixels_at_grows_cel_for_distant_pixels(sprite: str) -> None:
    """Pixels far outside an existing small cel must still be written.

    Regression: Aseprite cels are only as large as their content's bounding
    box, and putPixel() outside that box is silently discarded. The tool
    reported success while writing nothing, which repeatedly produced
    portraits with a missing mouth.
    """
    ok(run(canvas.add_layer(sprite, "far")))
    # Seed a tiny cel in one corner.
    ok(
        run(
            drawing.draw_pixels_at(
                sprite, "far", 1, [{"x": 1, "y": 1, "color": "#FF0000"}]
            )
        )
    )
    # Write well outside that cel's bounds.
    ok(
        run(
            drawing.draw_pixels_at(
                sprite, "far", 1, [{"x": 28, "y": 28, "color": "#00FF00"}]
            )
        )
    )
    r, g, b, _ = _rgba(run(pixel_read.get_pixel_color(sprite, 28, 28, "far", 1)))
    assert (r, g, b) == (0, 255, 0), (r, g, b)


def test_draw_pixels_at_warns_on_offcanvas_pixels(sprite: str) -> None:
    """Pixels outside the CANVAS cannot be drawn, so say so explicitly."""
    ok(run(canvas.add_layer(sprite, "oob")))
    result = run(
        drawing.draw_pixels_at(
            sprite,
            "oob",
            1,
            [
                {"x": 5, "y": 5, "color": "#FF0000"},
                {"x": 500, "y": 500, "color": "#FF0000"},
            ],
        )
    )
    assert "WARNING" in str(result), result
