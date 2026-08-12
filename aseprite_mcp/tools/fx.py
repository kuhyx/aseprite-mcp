from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.colors import parse_hex_color
from ..core.commands import AsepriteCommand, lua_escape
from ..core.lua import FIND_LAYER, HSL, NORMALIZE_CEL, PSET
from ..core.paths import path_exists


def _parse_hex_color(value: str) -> tuple[int, int, int] | None:
    """RGB-only parse (alpha dropped); unified via core.colors.parse_hex_color."""
    rgba = parse_hex_color(value)
    return rgba[:3] if rgba else None


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def outline_cel(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Layer to outline")],
    frame_index: Annotated[int, Field(description="Frame index starting at 1")],
    color: Annotated[str, Field(description="Outline hex color")] = "#000000",
    include_diagonals: Annotated[
        bool,
        Field(
            description="Also outline diagonal neighbors for a thicker, rounded outline"
        ),
    ] = False,
) -> str:
    """Add a 1px outline around all opaque pixels of a cel.

    Transparent pixels adjacent to opaque pixels are filled with the
    outline color. Great for making sprites read clearly against any
    background.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    rgb = _parse_hex_color(color)
    if rgb is None:
        return f"Invalid color value: {color}"
    r, g, b = rgb
    diag = "true" if include_diagonals else "false"

    safe_layer = lua_escape(layer_name)
    script = f"""
    {FIND_LAYER}
    {NORMALIZE_CEL}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end

    app.transaction(function()
        local cel = normalize_cel(spr, target, spr.frames[idx], false)
        if not cel then print("ERROR:No cel at that layer/frame") return end
        local img = cel.image
        local src = img:clone()
        local outline = app.pixelColor.rgba({r}, {g}, {b}, 255)

        local function opaque(x, y)
            if x < 0 or y < 0 or x >= src.width or y >= src.height then return false end
            return app.pixelColor.rgbaA(src:getPixel(x, y)) > 0
        end

        for py = 0, img.height - 1 do
            for px = 0, img.width - 1 do
                if app.pixelColor.rgbaA(src:getPixel(px, py)) == 0 then
                    local touch = opaque(px - 1, py) or opaque(px + 1, py)
                                  or opaque(px, py - 1) or opaque(px, py + 1)
                    if not touch and {diag} then
                        touch = opaque(px - 1, py - 1) or opaque(px + 1, py - 1)
                                or opaque(px - 1, py + 1) or opaque(px + 1, py + 1)
                    end
                    if touch then
                        img:putPixel(px, py, outline)
                    end
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Outline added to '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to outline cel: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def replace_color(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Layer to operate on")],
    frame_index: Annotated[int, Field(description="Frame index starting at 1")],
    from_color: Annotated[
        str, Field(description='Hex color to replace, e.g. "#FF0000"')
    ],
    to_color: Annotated[str, Field(description="Replacement hex color")],
    tolerance: Annotated[
        int, Field(description="Per-channel tolerance 0-255; 0 means exact match")
    ] = 0,
) -> str:
    """Replace one color with another in a cel, preserving alpha."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    src = _parse_hex_color(from_color)
    dst = _parse_hex_color(to_color)
    if src is None or dst is None:
        return "Colors must use #RRGGBB values"
    if tolerance < 0 or tolerance > 255:
        return "Tolerance must be between 0 and 255"
    sr, sg, sb = src
    dr, dg, db = dst

    safe_layer = lua_escape(layer_name)
    script = f"""
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end

    local cel = target:cel(spr.frames[idx])
    if not cel then print("ERROR:No cel at that layer/frame") return end

    local count = 0
    app.transaction(function()
        local img = cel.image
        for py = 0, img.height - 1 do
            for px = 0, img.width - 1 do
                local v = img:getPixel(px, py)
                local a = app.pixelColor.rgbaA(v)
                if a > 0 then
                    local cr = math.abs(app.pixelColor.rgbaR(v) - {sr})
                    local cg = math.abs(app.pixelColor.rgbaG(v) - {sg})
                    local cb = math.abs(app.pixelColor.rgbaB(v) - {sb})
                    if cr <= {tolerance} and cg <= {tolerance} and cb <= {tolerance} then
                        img:putPixel(px, py, app.pixelColor.rgba({dr}, {dg}, {db}, a))
                        count = count + 1
                    end
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("COUNT:" .. count)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to replace color: {output}"

    count = "?"
    for line in output.splitlines():
        if line.startswith("COUNT:"):
            count = line[len("COUNT:") :]
    return (
        f"Replaced {count} pixels {from_color} -> {to_color} on '{layer_name}' "
        f"frame {frame_index} in {filename}"
    )


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def adjust_hsl(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Layer to adjust")],
    frame_index: Annotated[int, Field(description="Frame index starting at 1")],
    hue_shift: Annotated[
        float, Field(description="Degrees to rotate hue, -360 to 360")
    ] = 0,
    saturation_shift: Annotated[
        float, Field(description="Saturation delta, -100 to 100")
    ] = 0,
    lightness_shift: Annotated[
        float, Field(description="Lightness delta, -100 to 100")
    ] = 0,
) -> str:
    """Shift hue, saturation, and lightness of all opaque pixels in a cel.

    Useful for creating palette-swapped variants and shading: e.g. darken
    a duplicated layer for shadows or hue-shift toward blue for night
    scenes. Shifts are relative and accumulate each time this is called
    on the same cel.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not (-360 <= hue_shift <= 360):
        return "hue_shift must be between -360 and 360"
    if not (-100 <= saturation_shift <= 100):
        return "saturation_shift must be between -100 and 100"
    if not (-100 <= lightness_shift <= 100):
        return "lightness_shift must be between -100 and 100"

    safe_layer = lua_escape(layer_name)
    script = f"""
    {FIND_LAYER}
    {HSL}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end

    local cel = target:cel(spr.frames[idx])
    if not cel then print("ERROR:No cel at that layer/frame") return end

    app.transaction(function()
        local img = cel.image
        for py = 0, img.height - 1 do
            for px = 0, img.width - 1 do
                local v = img:getPixel(px, py)
                local a = app.pixelColor.rgbaA(v)
                if a > 0 then
                    local h, s, l = rgb_to_hsl(
                        app.pixelColor.rgbaR(v),
                        app.pixelColor.rgbaG(v),
                        app.pixelColor.rgbaB(v))
                    h = h + ({hue_shift})
                    s = math.min(1, math.max(0, s + ({saturation_shift}) / 100))
                    l = math.min(1, math.max(0, l + ({lightness_shift}) / 100))
                    local nr, ng, nb = hsl_to_rgb(h, s, l)
                    img:putPixel(px, py, app.pixelColor.rgba(nr, ng, nb, a))
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Adjusted HSL (h{hue_shift:+g}, s{saturation_shift:+g}, l{lightness_shift:+g}) "
            f"on '{layer_name}' frame {frame_index} in {filename}"
        )
    return f"Failed to adjust HSL: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def apply_dither_gradient(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Layer to draw on")],
    frame_index: Annotated[int, Field(description="Frame index starting at 1")],
    x: Annotated[int, Field(description="Left edge of the rectangle")],
    y: Annotated[int, Field(description="Top edge of the rectangle")],
    width: Annotated[int, Field(description="Rectangle width")],
    height: Annotated[int, Field(description="Rectangle height")],
    color_start: Annotated[
        str, Field(description="Hex color at the start of the gradient")
    ],
    color_end: Annotated[
        str, Field(description="Hex color at the end of the gradient")
    ],
    horizontal: Annotated[
        bool,
        Field(description="Run the gradient left-to-right instead of top-to-bottom"),
    ] = False,
    create_if_missing: Annotated[
        bool, Field(description="Create the cel if it does not exist")
    ] = True,
) -> str:
    """Fill a rectangle with a two-color gradient using Bayer 4x4 ordered dithering.

    This is the classic pixel-art way to blend two colors without
    introducing new intermediate colors. The gradient runs from
    color_start (top/left) to color_end (bottom/right).
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    start = _parse_hex_color(color_start)
    end = _parse_hex_color(color_end)
    if start is None or end is None:
        return "Colors must use #RRGGBB values"
    r1, g1, b1 = start
    r2, g2, b2 = end
    create = "true" if create_if_missing else "false"
    axis = "px - " + str(x) if horizontal else "py - " + str(y)
    span = width if horizontal else height

    safe_layer = lua_escape(layer_name)
    script = f"""
    {FIND_LAYER}
    {NORMALIZE_CEL}
    {PSET}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end

    local bayer = {{
        {{ 0,  8,  2, 10}},
        {{12,  4, 14,  6}},
        {{ 3, 11,  1,  9}},
        {{15,  7, 13,  5}},
    }}

    app.transaction(function()
        local cel = normalize_cel(spr, target, spr.frames[idx], {create})
        if not cel then print("ERROR:No cel at that layer/frame") return end
        local img = cel.image
        local c1 = app.pixelColor.rgba({r1}, {g1}, {b1}, 255)
        local c2 = app.pixelColor.rgba({r2}, {g2}, {b2}, 255)
        for py = {y}, {y} + {height} - 1 do
            for px = {x}, {x} + {width} - 1 do
                local f = ({axis}) / math.max(1, {span} - 1)
                local threshold = (bayer[(py % 4) + 1][(px % 4) + 1] + 0.5) / 16
                if f >= threshold then
                    pset(img, px, py, c2)
                else
                    pset(img, px, py, c1)
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        direction = "horizontal" if horizontal else "vertical"
        return (
            f"Dithered {direction} gradient {color_start} -> {color_end} applied at "
            f"({x},{y}) {width}x{height} on '{layer_name}' frame {frame_index} in {filename}"
        )
    return f"Failed to apply dither gradient: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def apply_dither_pattern(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Layer to draw on")],
    frame_index: Annotated[int, Field(description="Frame index starting at 1")],
    x: Annotated[int, Field(description="Left edge of the rectangle")],
    y: Annotated[int, Field(description="Top edge of the rectangle")],
    width: Annotated[int, Field(description="Rectangle width")],
    height: Annotated[int, Field(description="Rectangle height")],
    color_a: Annotated[str, Field(description="Base hex color")],
    color_b: Annotated[str, Field(description="Mixed-in hex color")],
    density: Annotated[
        float,
        Field(
            description=(
                "Fraction of color_b, 0.0-1.0: 0.0 is all color_a, 0.5 is a "
                "checkerboard, 1.0 is all color_b"
            )
        ),
    ] = 0.5,
    create_if_missing: Annotated[
        bool, Field(description="Create the cel if it does not exist")
    ] = True,
) -> str:
    """Fill a rectangle with a uniform Bayer-dithered mix of two colors.

    Useful for textures (stone, grass) and flat mid-tones between two
    palette colors.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"
    if not (0 <= density <= 1):
        return "density must be between 0.0 and 1.0"

    a = _parse_hex_color(color_a)
    b = _parse_hex_color(color_b)
    if a is None or b is None:
        return "Colors must use #RRGGBB values"
    r1, g1, b1 = a
    r2, g2, b2 = b
    create = "true" if create_if_missing else "false"

    safe_layer = lua_escape(layer_name)
    script = f"""
    {FIND_LAYER}
    {NORMALIZE_CEL}
    {PSET}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end

    local bayer = {{
        {{ 0,  8,  2, 10}},
        {{12,  4, 14,  6}},
        {{ 3, 11,  1,  9}},
        {{15,  7, 13,  5}},
    }}

    app.transaction(function()
        local cel = normalize_cel(spr, target, spr.frames[idx], {create})
        if not cel then print("ERROR:No cel at that layer/frame") return end
        local img = cel.image
        local ca = app.pixelColor.rgba({r1}, {g1}, {b1}, 255)
        local cb = app.pixelColor.rgba({r2}, {g2}, {b2}, 255)
        for py = {y}, {y} + {height} - 1 do
            for px = {x}, {x} + {width} - 1 do
                local threshold = (bayer[(py % 4) + 1][(px % 4) + 1] + 0.5) / 16
                if {density} > threshold then
                    pset(img, px, py, cb)
                else
                    pset(img, px, py, ca)
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Dither pattern ({color_a}/{color_b}, density {density}) applied at "
            f"({x},{y}) {width}x{height} on '{layer_name}' frame {frame_index} in {filename}"
        )
    return f"Failed to apply dither pattern: {output}"
