from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.colors import parse_hex_color
from ..core.commands import AsepriteCommand, lua_escape
from ..core.lua import FIND_LAYER, GROW_CEL, NORMALIZE_CEL, PSET, REQUIRE_CEL
from ..core.paths import path_exists

_OK_MARKER_FIELD_COUNT = 3
_MIN_POLYGON_POINTS = 3
_MIN_PATH_POINTS = 2


def _parse_write_counts(output: str, total: int) -> tuple[int, int]:
    """Read the 'OK:<written>:<skipped>' marker emitted by draw_pixels_at.

    Falls back to assuming everything landed when the marker is absent, so
    older scripts keep working.
    """
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith("OK:"):
            parts = line.split(":")
            if len(parts) >= _OK_MARKER_FIELD_COUNT:
                try:
                    return int(parts[1]), int(parts[2])
                except ValueError:
                    break
    return total, 0


def _parse_hex_color(value: str) -> tuple[int, int, int, int] | None:
    """Parse a hex colour to (r, g, b, a); accepts #RRGGBB and #RRGGBBAA."""
    return parse_hex_color(value)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_pixels(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    pixels: Annotated[
        list[dict[str, Any]],
        Field(
            description=(
                'List of pixels to set, each a dict {"x": int, "y": int, '
                '"color": str} where color is a hex code like "#FF0000" or '
                '"#FF0000FF"'
            )
        ),
    ],
) -> str:
    """Draw individual pixels on the active cel with specified colors.

    Operates on app.activeCel (falling back to layer 1 / frame 1 if there is
    no active cel). For multi-layer or multi-frame sprites, prefer
    draw_pixels_at, which targets a named layer and frame index explicitly.

    The cel is grown to fit pixels outside its current bounds, so drawing in
    a previously-empty area works. Pixels outside the CANVAS are still
    impossible and are reported as skipped.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    # Bounding box of every requested pixel, so the cel can be grown to fit.
    xs = [int(p.get("x", 0)) for p in pixels]
    ys = [int(p.get("y", 0)) for p in pixels]
    if xs and ys:
        need_x, need_y = min(xs), min(ys)
        need_w, need_h = max(xs) - need_x + 1, max(ys) - need_y + 1
    else:
        need_x = need_y = 0
        need_w = need_h = 1

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {GROW_CEL}

    local layer = app.activeLayer or spr.layers[1]
    local frame = app.activeFrame or spr.frames[1]

    app.transaction(function()
        app.activeLayer = layer
        app.activeFrame = frame
        local cel = grow_cel(spr, layer, frame,
                             {need_x}, {need_y}, {need_w}, {need_h})

        local img = cel.image
        local cox = cel.position.x
        local coy = cel.position.y
    """

    # Add pixel drawing commands. Coordinates are sprite-global; we
    # offset into cel-local space because cel.image:putPixel uses
    # cel-local coordinates.
    for pixel in pixels:
        x = pixel.get("x", 0)
        y = pixel.get("y", 0)
        rgb = _parse_hex_color(pixel.get("color", "#000000"))
        if rgb is None:
            return f"Invalid color value: {pixel.get('color')}"
        r, g, b, a = rgb

        script += f"""
        img:putPixel({x} - cox, {y} - coy, Color({r}, {g}, {b}, {a}))
        """

    script += """
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"Pixels drawn successfully in {filename}"
    return f"Failed to draw pixels: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_line(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    x1: Annotated[int, Field(description="Starting x coordinate (sprite-global)")],
    y1: Annotated[int, Field(description="Starting y coordinate (sprite-global)")],
    x2: Annotated[int, Field(description="Ending x coordinate (sprite-global)")],
    y2: Annotated[int, Field(description="Ending y coordinate (sprite-global)")],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    thickness: Annotated[int, Field(description="Line thickness in pixels")] = 1,
) -> str:
    """Draw a straight line on the active cel using Bresenham's algorithm.

    Operates on app.activeCel (falling back to layer 1 / frame 1 if there is
    no active cel). For multi-layer or multi-frame sprites, prefer
    draw_line_at, which targets a named layer and frame index explicitly.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb

    # Bounding box of the line, widened by put_thick's radius so a thick
    # line's outer edge is inside the grown cel too.
    radius = max(0, thickness // 2)
    need_x = min(x1, x2) - radius
    need_y = min(y1, y2) - radius
    need_w = abs(x2 - x1) + 1 + 2 * radius
    need_h = abs(y2 - y1) + 1 + 2 * radius

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {GROW_CEL}

    local function put_thick(img, x, y, color, size)
        local r = math.max(0, math.floor(size / 2))
        for oy = -r, r do
            for ox = -r, r do
                img:putPixel(x + ox, y + oy, color)
            end
        end
    end

    local function draw_line(img, x0, y0, x1, y1, color, size)
        local dx = math.abs(x1 - x0)
        local sx = x0 < x1 and 1 or -1
        local dy = -math.abs(y1 - y0)
        local sy = y0 < y1 and 1 or -1
        local err = dx + dy
        while true do
            if size > 1 then
                put_thick(img, x0, y0, color, size)
            else
                img:putPixel(x0, y0, color)
            end
            if x0 == x1 and y0 == y1 then break end
            local e2 = 2 * err
            if e2 >= dy then err = err + dy; x0 = x0 + sx end
            if e2 <= dx then err = err + dx; y0 = y0 + sy end
        end
    end

    local layer = app.activeLayer or spr.layers[1]
    local frame = app.activeFrame or spr.frames[1]

    app.transaction(function()
        app.activeLayer = layer
        app.activeFrame = frame
        local cel = grow_cel(spr, layer, frame,
                             {need_x}, {need_y}, {need_w}, {need_h})
        local img = cel.image
        local cox = cel.position.x
        local coy = cel.position.y
        local color = Color({r}, {g}, {b}, {a})
        -- Translate sprite-global args into cel-local space so the
        -- inner Bresenham/putPixel helpers do not need to know about
        -- cel.position.
        draw_line(img, {x1} - cox, {y1} - coy, {x2} - cox, {y2} - coy, color, {thickness})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"Line drawn successfully in {filename}"
    return f"Failed to draw line: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_rectangle(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    x: Annotated[int, Field(description="Top-left x coordinate (sprite-global)")],
    y: Annotated[int, Field(description="Top-left y coordinate (sprite-global)")],
    width: Annotated[
        int, Field(description="Width of the rectangle in pixels; must be > 0")
    ],
    height: Annotated[
        int, Field(description="Height of the rectangle in pixels; must be > 0")
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    fill: Annotated[
        bool,
        Field(description="Fill the rectangle instead of only drawing its outline"),
    ] = False,
) -> str:
    """Draw a rectangle outline or filled rectangle on the active cel.

    Operates on app.activeCel (falling back to layer 1 / frame 1 if there is
    no active cel). For multi-layer or multi-frame sprites, prefer
    draw_rectangle_at, which targets a named layer and frame index
    explicitly.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb

    # app.useTool treats both points as inclusive corners, so the second
    # point sits at (x+width-1, y+height-1) for a width x height rect.
    x2 = x + width - 1
    y2 = y + height - 1

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        local cel = app.activeCel
        if not cel then
            app.activeLayer = spr.layers[1]
            app.activeFrame = spr.frames[1]
            cel = app.activeCel
            if not cel then
                print("ERROR:No active cel and couldn't create one") return
            end
        end

        local color = Color({r}, {g}, {b}, {a})
        local tool = {'"rectangle"' if not fill else '"filled_rectangle"'}
        app.useTool({{
            tool=tool,
            color=color,
            points={{Point({x}, {y}), Point({x2}, {y2})}}
        }})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"Rectangle drawn successfully in {filename}"
    return f"Failed to draw rectangle: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def fill_area(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    x: Annotated[
        int,
        Field(description="X coordinate to start the flood fill from (sprite-global)"),
    ],
    y: Annotated[
        int,
        Field(description="Y coordinate to start the flood fill from (sprite-global)"),
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
) -> str:
    """Flood-fill a contiguous area with color using the paint bucket tool.

    Operates on app.activeCel (falling back to layer 1 / frame 1 if there is
    no active cel). For multi-layer or multi-frame sprites, prefer
    fill_area_at, which targets a named layer and frame index explicitly.
    Because the fill region depends on current cel content, calling this
    twice at the same point is not guaranteed to produce the same result if
    the surrounding pixels changed between calls.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        local cel = app.activeCel
        if not cel then
            app.activeLayer = spr.layers[1]
            app.activeFrame = spr.frames[1]
            cel = app.activeCel
            if not cel then
                print("ERROR:No active cel and couldn't create one") return
            end
        end

        local color = Color({r}, {g}, {b}, {a})
        app.useTool({{
            tool="paint_bucket",
            color=color,
            points={{Point({x}, {y})}}
        }})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"Area filled successfully in {filename}"
    return f"Failed to fill area: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_circle(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    center_x: Annotated[
        int, Field(description="X coordinate of the circle's center (sprite-global)")
    ],
    center_y: Annotated[
        int, Field(description="Y coordinate of the circle's center (sprite-global)")
    ],
    radius: Annotated[
        int, Field(description="Radius of the circle in pixels; must be > 0")
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    fill: Annotated[
        bool, Field(description="Fill the circle instead of only drawing its outline")
    ] = False,
) -> str:
    """Draw a circle outline or filled circle on the active cel.

    Operates on app.activeCel (falling back to layer 1 / frame 1 if there is
    no active cel). For multi-layer or multi-frame sprites, prefer
    draw_circle_at, which targets a named layer and frame index explicitly.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if radius <= 0:
        return "Radius must be > 0"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        local cel = app.activeCel
        if not cel then
            app.activeLayer = spr.layers[1]
            app.activeFrame = spr.frames[1]
            cel = app.activeCel
            if not cel then
                print("ERROR:No active cel and couldn't create one") return
            end
        end

        local color = Color({r}, {g}, {b}, {a})
        local tool = {'"ellipse"' if not fill else '"filled_ellipse"'}
        app.useTool({{
            tool=tool,
            color=color,
            points={{
                Point({center_x - radius}, {center_y - radius}),
                Point({center_x + radius}, {center_y + radius})
            }}
        }})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"Circle drawn successfully in {filename}"
    return f"Failed to draw circle: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_pixels_at(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    pixels: Annotated[
        list[dict[str, Any]],
        Field(
            description=(
                'List of pixels to set, each a dict {"x": int, "y": int, '
                '"color": str} where color is a hex code like "#FF0000" or '
                '"#FF0000FF"'
            )
        ),
    ],
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Draw pixels on a specific layer and frame, growing the cel to fit.

    Unlike draw_pixels, this grows the target cel's bounding box to cover
    every requested pixel (clipped to the canvas) before writing, so pixels
    in a previously-empty area of the cel are not silently discarded. Use
    this whenever drawing on a named layer/frame, or when adding new
    content outside an existing cel's current bounds.

    Returns:
        A summary noting how many pixels were written, and a WARNING with
        the count of any pixels that fell outside the canvas and were
        discarded.

    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"

    # Bounding box of every requested pixel, so the cel can be grown to fit.
    xs = [int(p.get("x", 0)) for p in pixels]
    ys = [int(p.get("y", 0)) for p in pixels]
    if xs and ys:
        need_x, need_y = min(xs), min(ys)
        need_w, need_h = max(xs) - need_x + 1, max(ys) - need_y + 1
    else:
        need_x = need_y = 0
        need_w = need_h = 1

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    {REQUIRE_CEL}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    -- Declared outside the transaction so the summary survives to the print.
    local written = 0
    local skipped = 0

    if not require_cel(target, spr.frames[idx], {create_flag}) then return end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = target:cel(spr.frames[idx])
        if not cel then
            local img = Image(spr.width, spr.height, spr.colorMode)
            cel = spr:newCel(target, spr.frames[idx], img, Point(0, 0))
        end

        -- Grow the cel so every requested pixel is inside it.
        --
        -- Aseprite cels are only as large as their content's bounding box.
        -- putPixel() outside that box is SILENTLY DISCARDED, so a caller
        -- adding a feature in a fresh area (a mouth, a hairclip) got "OK"
        -- back while nothing was written. Union the cel bounds with the
        -- requested pixel bounds first, clipped to the sprite.
        local need = Rectangle({need_x}, {need_y}, {need_w}, {need_h})
        local cur = Rectangle(cel.bounds)
        local union = cur:union(need)
        local canvas = Rectangle(0, 0, spr.width, spr.height)
        union = union:intersect(canvas)
        if union.width > cur.width or union.height > cur.height
           or union.x < cur.x or union.y < cur.y then
            local grown = Image(union.width, union.height, spr.colorMode)
            grown:clear()
            grown:drawImage(cel.image, Point(cur.x - union.x, cur.y - union.y))
            spr:newCel(target, spr.frames[idx], grown, Point(union.x, union.y))
            cel = target:cel(spr.frames[idx])
        end

        local img = cel.image
        local cox = cel.position.x
        local coy = cel.position.y
        local function put(px, py, col)
            -- Outside the sprite canvas can never be drawn; count it as
            -- skipped so the caller is told rather than silently losing it.
            if px < 0 or py < 0 or px >= spr.width or py >= spr.height then
                skipped = skipped + 1
                return
            end
            local lx, ly = px - cox, py - coy
            if lx >= 0 and ly >= 0 and lx < img.width and ly < img.height then
                img:putPixel(lx, ly, col)
                written = written + 1
            else
                skipped = skipped + 1
            end
        end
    """

    for pixel in pixels:
        x = pixel.get("x", 0)
        y = pixel.get("y", 0)
        rgb = _parse_hex_color(pixel.get("color", "#000000"))
        if rgb is None:
            return f"Invalid color value: {pixel.get('color')}"
        r, g, b, a = rgb
        script += f"""
        put({x}, {y}, Color({r}, {g}, {b}, {a}))
        """

    script += """
    end)

    spr:saveAs(spr.filename)
    print("OK:" .. tostring(written) .. ":" .. tostring(skipped))
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to draw pixels: {output}"

    # Surface partial writes instead of reporting a blanket success.
    written, skipped = _parse_write_counts(output, len(pixels))
    if skipped:
        return (
            f"WARNING: only {written}/{len(pixels)} pixels written on "
            f"'{layer_name}' frame {frame_index}; {skipped} fell outside the "
            f"canvas and were discarded."
        )
    return (
        f"Pixels drawn on '{layer_name}' frame {frame_index} in {filename} "
        f"({written} pixels)"
    )


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_line_at(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    x1: Annotated[int, Field(description="Starting x coordinate (sprite-global)")],
    y1: Annotated[int, Field(description="Starting y coordinate (sprite-global)")],
    x2: Annotated[int, Field(description="Ending x coordinate (sprite-global)")],
    y2: Annotated[int, Field(description="Ending y coordinate (sprite-global)")],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    thickness: Annotated[int, Field(description="Line thickness in pixels")] = 1,
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Draw a straight line on a specific layer and frame.

    The layer/frame-targeted counterpart of draw_line — use this for
    multi-layer or multi-frame sprites instead of relying on the active
    cel.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb
    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local function put_thick(img, x, y, color, size)
        local r = math.max(0, math.floor(size / 2))
        for oy = -r, r do
            for ox = -r, r do
                img:putPixel(x + ox, y + oy, color)
            end
        end
    end

    local function draw_line(img, x0, y0, x1, y1, color, size)
        local dx = math.abs(x1 - x0)
        local sx = x0 < x1 and 1 or -1
        local dy = -math.abs(y1 - y0)
        local sy = y0 < y1 and 1 or -1
        local err = dx + dy
        while true do
            if size > 1 then
                put_thick(img, x0, y0, color, size)
            else
                img:putPixel(x0, y0, color)
            end
            if x0 == x1 and y0 == y1 then break end
            local e2 = 2 * err
            if e2 >= dy then err = err + dy; x0 = x0 + sx end
            if e2 <= dx then err = err + dx; y0 = y0 + sy end
        end
    end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    {REQUIRE_CEL}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    if not require_cel(target, spr.frames[idx], {create_flag}) then return end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = target:cel(spr.frames[idx])
        if not cel then
            local img = Image(spr.width, spr.height, spr.colorMode)
            cel = spr:newCel(target, spr.frames[idx], img, Point(0, 0))
        end
        local img = cel.image
        local cox = cel.position.x
        local coy = cel.position.y
        local color = Color({r}, {g}, {b}, {a})
        draw_line(img, {x1} - cox, {y1} - coy, {x2} - cox, {y2} - coy, color, {thickness})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Line drawn on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to draw line: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_rectangle_at(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    x: Annotated[int, Field(description="Top-left x coordinate (sprite-global)")],
    y: Annotated[int, Field(description="Top-left y coordinate (sprite-global)")],
    width: Annotated[
        int, Field(description="Width of the rectangle in pixels; must be > 0")
    ],
    height: Annotated[
        int, Field(description="Height of the rectangle in pixels; must be > 0")
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    fill: Annotated[
        bool,
        Field(description="Fill the rectangle instead of only drawing its outline"),
    ] = False,
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Draw a rectangle outline or filled rectangle on a specific layer/frame.

    The layer/frame-targeted counterpart of draw_rectangle — use this for
    multi-layer or multi-frame sprites instead of relying on the active
    cel.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb
    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"
    x2 = x + width - 1
    y2 = y + height - 1

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    {REQUIRE_CEL}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    if not require_cel(target, spr.frames[idx], {create_flag}) then return end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = target:cel(spr.frames[idx])
        if not cel then
            local img = Image(spr.width, spr.height, spr.colorMode)
            cel = spr:newCel(target, spr.frames[idx], img, Point(0, 0))
        end
        local color = Color({r}, {g}, {b}, {a})
        local tool = {'"rectangle"' if not fill else '"filled_rectangle"'}
        app.useTool({{
            tool=tool,
            color=color,
            points={{Point({x}, {y}), Point({x2}, {y2})}}
        }})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Rectangle drawn on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to draw rectangle: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_circle_at(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    center_x: Annotated[
        int, Field(description="X coordinate of the circle's center (sprite-global)")
    ],
    center_y: Annotated[
        int, Field(description="Y coordinate of the circle's center (sprite-global)")
    ],
    radius: Annotated[
        int, Field(description="Radius of the circle in pixels; must be > 0")
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    fill: Annotated[
        bool, Field(description="Fill the circle instead of only drawing its outline")
    ] = False,
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Draw a circle outline or filled circle on a specific layer/frame.

    The layer/frame-targeted counterpart of draw_circle — use this for
    multi-layer or multi-frame sprites instead of relying on the active
    cel.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if radius <= 0:
        return "Radius must be > 0"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb
    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    {REQUIRE_CEL}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    if not require_cel(target, spr.frames[idx], {create_flag}) then return end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = target:cel(spr.frames[idx])
        if not cel then
            local img = Image(spr.width, spr.height, spr.colorMode)
            cel = spr:newCel(target, spr.frames[idx], img, Point(0, 0))
        end
        local color = Color({r}, {g}, {b}, {a})
        local tool = {'"ellipse"' if not fill else '"filled_ellipse"'}
        app.useTool({{
            tool=tool,
            color=color,
            points={{
                Point({center_x - radius}, {center_y - radius}),
                Point({center_x + radius}, {center_y + radius})
            }}
        }})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Circle drawn on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to draw circle: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def fill_area_at(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    x: Annotated[
        int,
        Field(description="X coordinate to start the flood fill from (sprite-global)"),
    ],
    y: Annotated[
        int,
        Field(description="Y coordinate to start the flood fill from (sprite-global)"),
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Flood-fill a contiguous area on a specific layer/frame.

    The layer/frame-targeted counterpart of fill_area — use this for
    multi-layer or multi-frame sprites instead of relying on the active
    cel. Because the fill region depends on current cel content, calling
    this twice at the same point is not guaranteed to produce the same
    result if the surrounding pixels changed between calls.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb
    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    {REQUIRE_CEL}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    if not require_cel(target, spr.frames[idx], {create_flag}) then return end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = target:cel(spr.frames[idx])
        if not cel then
            local img = Image(spr.width, spr.height, spr.colorMode)
            cel = spr:newCel(target, spr.frames[idx], img, Point(0, 0))
        end
        local color = Color({r}, {g}, {b}, {a})
        app.useTool({{
            tool="paint_bucket",
            color=color,
            points={{Point({x}, {y})}}
        }})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Area filled on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to fill area: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_polygon(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    points: Annotated[
        list[dict[str, int]],
        Field(
            description='Ordered vertices of the polygon, each a dict {"x": int, "y": int}; at least 3 required'
        ),
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    fill: Annotated[
        bool,
        Field(
            description="Fill the polygon interior instead of only drawing its outline"
        ),
    ] = False,
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Draw a closed polygon outline or filled polygon on a specific layer/frame.

    The vertices are connected in order and the shape is closed back to the
    first vertex automatically.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if len(points) < _MIN_POLYGON_POINTS:
        return f"Polygon requires at least {_MIN_POLYGON_POINTS} points"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb
    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"
    fill_flag = "true" if fill else "false"
    points_lua = ", ".join([f"{{x={p['x']}, y={p['y']}}}" for p in points])

    script = f"""
    {NORMALIZE_CEL}
    {PSET}
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    -- Points are sprite-global; normalize_cel anchors the cel at (0,0)
    -- canvas-sized, so no cel-offset math is needed and pset() bounds-guards.
    local function draw_line(img, x0, y0, x1, y1, color)
        local dx = math.abs(x1 - x0)
        local sx = x0 < x1 and 1 or -1
        local dy = -math.abs(y1 - y0)
        local sy = y0 < y1 and 1 or -1
        local err = dx + dy
        while true do
            pset(img, x0, y0, color)
            if x0 == x1 and y0 == y1 then break end
            local e2 = 2 * err
            if e2 >= dy then err = err + dy; x0 = x0 + sx end
            if e2 <= dx then err = err + dx; y0 = y0 + sy end
        end
    end

    local function fill_polygon(img, pts, color)
        local minY = pts[1].y
        local maxY = pts[1].y
        for i = 2, #pts do
            if pts[i].y < minY then minY = pts[i].y end
            if pts[i].y > maxY then maxY = pts[i].y end
        end
        for y = minY, maxY do
            local nodes = {{}}
            local j = #pts
            for i = 1, #pts do
                local xi, yi = pts[i].x, pts[i].y
                local xj, yj = pts[j].x, pts[j].y
                if (yi < y and yj >= y) or (yj < y and yi >= y) then
                    local x = xi + (y - yi) * (xj - xi) / (yj - yi)
                    table.insert(nodes, x)
                end
                j = i
            end
            table.sort(nodes)
            for k = 1, #nodes, 2 do
                if nodes[k + 1] ~= nil then
                    local x_start = math.floor(nodes[k] + 0.5)
                    local x_end = math.floor(nodes[k + 1] + 0.5)
                    for x = x_start, x_end do
                        pset(img, x, y, color)
                    end
                end
            end
        end
    end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    if not target:cel(spr.frames[idx]) and not {create_flag} then
        print("ERROR:No cel at that layer/frame") return
    end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = normalize_cel(spr, target, spr.frames[idx], {create_flag})
        local img = cel.image
        local color = Color({r}, {g}, {b}, {a})
        local pts = {{ {points_lua} }}
        if {fill_flag} then
            fill_polygon(img, pts, color)
        end
        for i = 1, #pts do
            local n = i + 1
            if n > #pts then n = 1 end
            draw_line(img, pts[i].x, pts[i].y, pts[n].x, pts[n].y, color)
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Polygon drawn on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to draw polygon: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_path(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    points: Annotated[
        list[dict[str, int]],
        Field(
            description='Ordered vertices of the polyline, each a dict {"x": int, "y": int}; at least 2 required'
        ),
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    thickness: Annotated[int, Field(description="Line thickness in pixels")] = 1,
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Draw an open polyline through an ordered sequence of points.

    Unlike draw_polygon, the path is NOT closed back to the first point —
    use draw_polygon if you need a closed shape.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if len(points) < _MIN_PATH_POINTS:
        return f"Path requires at least {_MIN_PATH_POINTS} points"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb
    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"
    points_lua = ", ".join([f"{{x={p['x']}, y={p['y']}}}" for p in points])

    script = f"""
    {NORMALIZE_CEL}
    {PSET}
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local function put_thick(img, x, y, color, size)
        local rad = math.max(0, math.floor(size / 2))
        for oy = -rad, rad do
            for ox = -rad, rad do
                pset(img, x + ox, y + oy, color)
            end
        end
    end

    local function draw_line(img, x0, y0, x1, y1, color, size)
        local dx = math.abs(x1 - x0)
        local sx = x0 < x1 and 1 or -1
        local dy = -math.abs(y1 - y0)
        local sy = y0 < y1 and 1 or -1
        local err = dx + dy
        while true do
            if size > 1 then
                put_thick(img, x0, y0, color, size)
            else
                pset(img, x0, y0, color)
            end
            if x0 == x1 and y0 == y1 then break end
            local e2 = 2 * err
            if e2 >= dy then err = err + dy; x0 = x0 + sx end
            if e2 <= dx then err = err + dx; y0 = y0 + sy end
        end
    end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    if not target:cel(spr.frames[idx]) and not {create_flag} then
        print("ERROR:No cel at that layer/frame") return
    end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = normalize_cel(spr, target, spr.frames[idx], {create_flag})
        local img = cel.image
        local color = Color({r}, {g}, {b}, {a})
        local pts = {{ {points_lua} }}
        for i = 1, #pts - 1 do
            draw_line(img, pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y, color, {thickness})
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Path drawn on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to draw path: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def apply_gradient_rect(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    x: Annotated[
        int,
        Field(
            description="Top-left x coordinate of the gradient rectangle (sprite-global)"
        ),
    ],
    y: Annotated[
        int,
        Field(
            description="Top-left y coordinate of the gradient rectangle (sprite-global)"
        ),
    ],
    width: Annotated[
        int, Field(description="Width of the gradient rectangle in pixels; must be > 0")
    ],
    height: Annotated[
        int,
        Field(description="Height of the gradient rectangle in pixels; must be > 0"),
    ],
    color_start: Annotated[
        str,
        Field(
            description='Hex color code at the gradient\'s start edge, e.g. "#FF0000"'
        ),
    ],
    color_end: Annotated[
        str,
        Field(description='Hex color code at the gradient\'s end edge, e.g. "#0000FF"'),
    ],
    horizontal: Annotated[
        bool,
        Field(
            description="Interpolate left-to-right when True, top-to-bottom when False"
        ),
    ] = True,
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Fill a rectangle with a linear gradient between two colors.

    Each channel (r, g, b, a) is interpolated independently and linearly
    between color_start and color_end across the rectangle.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    start_rgb = _parse_hex_color(color_start)
    if start_rgb is None:
        return f"Invalid color_start value: {color_start}"
    end_rgb = _parse_hex_color(color_end)
    if end_rgb is None:
        return f"Invalid color_end value: {color_end}"

    sr, sg, sb, sa = start_rgb
    er, eg, eb, ea = end_rgb
    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"
    horiz_flag = "true" if horizontal else "false"

    script = f"""
    {NORMALIZE_CEL}
    {PSET}
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    if not target:cel(spr.frames[idx]) and not {create_flag} then
        print("ERROR:No cel at that layer/frame") return
    end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = normalize_cel(spr, target, spr.frames[idx], {create_flag})
        local img = cel.image
        local w = {width}
        local h = {height}
        for iy = 0, h - 1 do
            for ix = 0, w - 1 do
                local t = 0
                if {horiz_flag} then
                    t = (w > 1) and (ix / (w - 1)) or 0
                else
                    t = (h > 1) and (iy / (h - 1)) or 0
                end
                local r = math.floor({sr} + ({er} - {sr}) * t + 0.5)
                local g = math.floor({sg} + ({eg} - {sg}) * t + 0.5)
                local b = math.floor({sb} + ({eb} - {sb}) * t + 0.5)
                local a = math.floor({sa} + ({ea} - {sa}) * t + 0.5)
                pset(img, {x} + ix, {y} + iy, Color(r, g, b, a))
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Gradient applied on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to apply gradient: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def draw_ellipse_at(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to draw on")],
    frame_index: Annotated[
        int, Field(description="Frame index to draw on, starting at 1")
    ],
    center_x: Annotated[
        int, Field(description="X coordinate of the ellipse's center (sprite-global)")
    ],
    center_y: Annotated[
        int, Field(description="Y coordinate of the ellipse's center (sprite-global)")
    ],
    radius_x: Annotated[
        int, Field(description="Horizontal radius in pixels; must be > 0")
    ],
    radius_y: Annotated[
        int, Field(description="Vertical radius in pixels; must be > 0")
    ],
    color: Annotated[
        str, Field(description='Hex color code, e.g. "#FF0000" or "#FF0000FF"')
    ] = "#000000",
    fill: Annotated[
        bool, Field(description="Fill the ellipse instead of only drawing its outline")
    ] = False,
    create_if_missing: Annotated[
        bool,
        Field(
            description="Create the cel on that layer/frame if it does not already exist"
        ),
    ] = True,
) -> str:
    """Draw an ellipse outline or filled ellipse on a specific layer/frame.

    Use draw_circle_at instead when radius_x equals radius_y (a true
    circle) — this tool exists for the independently-scaled case.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if radius_x <= 0 or radius_y <= 0:
        return "radius_x and radius_y must be > 0"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b, a = rgb
    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_if_missing else "false"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    {REQUIRE_CEL}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    if not require_cel(target, spr.frames[idx], {create_flag}) then return end

    app.transaction(function()
        app.activeLayer = target
        app.activeFrame = spr.frames[idx]
        local cel = target:cel(spr.frames[idx])
        if not cel then
            local img = Image(spr.width, spr.height, spr.colorMode)
            cel = spr:newCel(target, spr.frames[idx], img, Point(0, 0))
        end
        local color = Color({r}, {g}, {b}, {a})
        local tool = {'"filled_ellipse"' if fill else '"ellipse"'}
        app.useTool({{
            tool=tool,
            color=color,
            points={{
                Point({center_x - radius_x}, {center_y - radius_y}),
                Point({center_x + radius_x}, {center_y + radius_y})
            }}
        }})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Ellipse drawn on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to draw ellipse: {output}"
