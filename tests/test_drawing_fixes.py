"""B3 (cel-normalization, no silent clip) + B4 (per-pixel alpha) fixes."""

from conftest import BASE, ok, run

from aseprite_mcp.core.commands import AsepriteCommand
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


# --- draw_pixels / draw_line: grow the cel like draw_pixels_at does ---
#
# These two write through raw putPixel in cel-local space. Before the fix a
# pixel outside the active cel's bounding box was silently discarded while
# the tool still reported success (verified: the pixel read back a=0 and the
# cel bounds never moved). The three sibling tools (draw_rectangle,
# fill_area, draw_circle) dispatch app.useTool, which grows the cel itself,
# so they never had this bug -- confirmed empirically before this fix.


def _shrink_cel_to_corner(sprite: str) -> None:
    """Replace layer 1's cel with a 2x2 cel anchored at (0,0).

    Gives the tests a deliberately small cel so "outside the bounds" is a
    meaningful position rather than a full-canvas no-op.
    """
    script = """
    local spr = app.activeSprite
    local img = Image(2, 2, spr.colorMode)
    img:clear()
    app.transaction(function()
        spr:newCel(spr.layers[1], spr.frames[1], img, Point(0, 0))
    end)
    spr:saveAs(spr.filename)
    print("OK")
    """
    success, output = AsepriteCommand.execute_lua_script_checked(script, sprite)
    assert success, output


def test_draw_pixels_grows_cel_beyond_bounds() -> None:
    fresh = f"{BASE}/grow_pixels.aseprite"
    ok(run(canvas.create_canvas(32, 32, fresh)))
    _shrink_cel_to_corner(fresh)
    ok(run(drawing.draw_pixels(fresh, [{"x": 20, "y": 20, "color": "#00FF00"}])))
    r, g, b, a = _rgba(run(pixel_read.get_composite_pixel(fresh, 20, 20, 1)))
    assert (r, g, b, a) == (0, 255, 0, 255), (r, g, b, a)


def test_draw_line_grows_cel_beyond_bounds() -> None:
    fresh = f"{BASE}/grow_line.aseprite"
    ok(run(canvas.create_canvas(32, 32, fresh)))
    _shrink_cel_to_corner(fresh)
    ok(run(drawing.draw_line(fresh, 20, 5, 28, 5, "#0000FF", 1)))
    r, g, b, a = _rgba(run(pixel_read.get_composite_pixel(fresh, 24, 5, 1)))
    assert (r, g, b, a) == (0, 0, 255, 255), (r, g, b, a)


def test_usetool_siblings_already_grow_the_cel() -> None:
    """draw_rectangle/fill_area/draw_circle grow the cel via app.useTool.

    Pins the behaviour that makes the union/regrow block unnecessary for
    these three, so a future change that switches them to putPixel fails
    here instead of silently dropping art.
    """
    fresh = f"{BASE}/grow_usetool.aseprite"
    ok(run(canvas.create_canvas(32, 32, fresh)))
    _shrink_cel_to_corner(fresh)
    ok(run(drawing.draw_rectangle(fresh, 20, 20, 6, 6, "#00FF00", fill=True)))
    r, g, b, a = _rgba(run(pixel_read.get_composite_pixel(fresh, 22, 22, 1)))
    assert (r, g, b, a) == (0, 255, 0, 255), (r, g, b, a)


def test_draw_pixels_empty_list_uses_fallback_bounds() -> None:
    """pixels=[] leaves xs/ys empty, hitting the 1x1 fallback bbox."""
    fresh = f"{BASE}/grow_pixels_empty.aseprite"
    ok(run(canvas.create_canvas(16, 16, fresh)))
    ok(run(drawing.draw_pixels(fresh, [])))
