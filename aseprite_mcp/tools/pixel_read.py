import json
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.commands import AsepriteCommand, lua_escape
from ..core.lua import FIND_LAYER
from ..core.paths import path_exists
from .analysis import _FLATTEN_FRAME


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def get_pixel_color(
    filename: Annotated[str, Field(description="Path to the Aseprite file to read")],
    x: Annotated[int, Field(description="X coordinate to read (sprite-global)")],
    y: Annotated[int, Field(description="Y coordinate to read (sprite-global)")],
    layer_name: Annotated[
        str,
        Field(description="Layer to read from; uses the active layer/cel when empty"),
    ] = "",
    frame_index: Annotated[
        int, Field(description="Frame index to read, starting at 1")
    ] = 1,
) -> str:
    """Read the RGBA color of a single pixel from one layer's cel.

    This reads only the named layer's own cel — it does not account for
    layers above it, opacity, or blend modes. Use get_composite_pixel
    instead when you need "what the player actually sees" at that pixel.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer = lua_escape(layer_name)
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local cel = nil
    if "{safe_layer}" ~= "" then
        {FIND_LAYER}
        local target = find_layer(spr, "{safe_layer}")
        if not target then print("ERROR:Layer not found") return end
        cel = target:cel(spr.frames[idx])
        if not cel then print("ERROR:No cel at that layer/frame") return end
    else
        app.activeFrame = spr.frames[idx]
        cel = app.activeCel
        if not cel then print("ERROR:No active cel") return end
    end

    local img = cel.image
    -- Coordinates are sprite-global; offset into cel-local space.
    local cx = {x} - cel.position.x
    local cy = {y} - cel.position.y
    local r, g, b, a = 0, 0, 0, 0
    if cx >= 0 and cy >= 0 and cx < img.width and cy < img.height then
        local px_val = img:getPixel(cx, cy)
        r = app.pixelColor.rgbaR(px_val)
        g = app.pixelColor.rgbaG(px_val)
        b = app.pixelColor.rgbaB(px_val)
        a = app.pixelColor.rgbaA(px_val)
    end
    print(string.format("PIXEL:%d,%d,%d,%d", r, g, b, a))
    """

    success, output = AsepriteCommand.execute_lua_script(script, filename)
    if not success:
        return f"Failed to read pixel: {output}"

    for line in output.splitlines():
        if line.startswith("ERROR:"):
            return f"Failed to read pixel: {line[6:]}"
        if line.startswith("PIXEL:"):
            parts = line[6:].split(",")
            r, g, b, a = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
            return f"#{r:02x}{g:02x}{b:02x} (r={r}, g={g}, b={b}, a={a})"

    return "No pixel data returned"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def get_pixels_rect(
    filename: Annotated[str, Field(description="Path to the Aseprite file to read")],
    x: Annotated[
        int, Field(description="Top-left x coordinate of the region (sprite-global)")
    ],
    y: Annotated[
        int, Field(description="Top-left y coordinate of the region (sprite-global)")
    ],
    width: Annotated[
        int, Field(description="Width of the region in pixels; must be > 0")
    ],
    height: Annotated[
        int, Field(description="Height of the region in pixels; must be > 0")
    ],
    layer_name: Annotated[
        str,
        Field(description="Layer to read from; uses the active layer/cel when empty"),
    ] = "",
    frame_index: Annotated[
        int, Field(description="Frame index to read, starting at 1")
    ] = 1,
) -> str:
    """Read all pixel colors in a rectangular region from one layer's cel.

    This reads only the named layer's own cel — it does not account for
    layers above it, opacity, or blend modes. Use get_composite_rect
    instead when you need "what the player actually sees" over that
    region.

    Returns:
        JSON array of {x, y, hex, r, g, b, a} objects

    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    safe_layer = lua_escape(layer_name)
    x_end = x + width - 1
    y_end = y + height - 1

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local cel = nil
    if "{safe_layer}" ~= "" then
        {FIND_LAYER}
        local target = find_layer(spr, "{safe_layer}")
        if not target then print("ERROR:Layer not found") return end
        cel = target:cel(spr.frames[idx])
        if not cel then print("ERROR:No cel at that layer/frame") return end
    else
        app.activeFrame = spr.frames[idx]
        cel = app.activeCel
        if not cel then print("ERROR:No active cel") return end
    end

    local img = cel.image
    local ox = cel.position.x
    local oy = cel.position.y
    local iw = img.width
    local ih = img.height

    for py = {y}, {y_end} do
        for px = {x}, {x_end} do
            local cx = px - ox
            local cy = py - oy
            local r, g, b, a = 0, 0, 0, 0
            if cx >= 0 and cy >= 0 and cx < iw and cy < ih then
                local px_val = img:getPixel(cx, cy)
                r = app.pixelColor.rgbaR(px_val)
                g = app.pixelColor.rgbaG(px_val)
                b = app.pixelColor.rgbaB(px_val)
                a = app.pixelColor.rgbaA(px_val)
            end
            print(string.format("PIXEL:%d,%d,%d,%d,%d,%d", px, py, r, g, b, a))
        end
    end
    """

    success, output = AsepriteCommand.execute_lua_script(script, filename)
    if not success:
        return f"Failed to read pixels: {output}"

    pixels = []
    for line in output.splitlines():
        if line.startswith("ERROR:"):
            return f"Failed to read pixels: {line[6:]}"
        if line.startswith("PIXEL:"):
            parts = line[6:].split(",")
            px, py, r, g, b, a = [int(p) for p in parts]
            pixels.append(
                {
                    "x": px,
                    "y": py,
                    "hex": f"#{r:02x}{g:02x}{b:02x}",
                    "r": r,
                    "g": g,
                    "b": b,
                    "a": a,
                }
            )

    if not pixels:
        return "No pixel data returned"
    return json.dumps(pixels)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def get_composite_pixel(
    filename: Annotated[str, Field(description="Path to the Aseprite file to read")],
    x: Annotated[int, Field(description="X coordinate to read (sprite-global)")],
    y: Annotated[int, Field(description="Y coordinate to read (sprite-global)")],
    frame_index: Annotated[
        int, Field(description="Frame index to read, starting at 1")
    ] = 1,
) -> str:
    """Read the RGBA colour VISIBLE at a pixel (flattened composite of all layers).

    Unlike get_pixel_color (which reads a single cel), this composites every
    visible layer — "what the player actually sees" — by flattening a throwaway
    clone. Essential for value/CVD QA on grouped/multi-layer scenes.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    script = f"""
    {_FLATTEN_FRAME}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end
    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end
    local clone = Sprite(spr)
    clone:flatten()
    local img = flatten_frame(clone, idx, nil)
    local r, g, b, a = 0, 0, 0, 0
    if {x} >= 0 and {y} >= 0 and {x} < img.width and {y} < img.height then
        local pv = img:getPixel({x}, {y})
        r = app.pixelColor.rgbaR(pv)
        g = app.pixelColor.rgbaG(pv)
        b = app.pixelColor.rgbaB(pv)
        a = app.pixelColor.rgbaA(pv)
    end
    print(string.format("PIXEL:%d,%d,%d,%d", r, g, b, a))
    """

    success, output = AsepriteCommand.execute_lua_script(script, filename)
    if not success:
        return f"Failed to read composite pixel: {output}"
    for line in output.splitlines():
        if line.startswith("ERROR:"):
            return f"Failed to read composite pixel: {line[6:]}"
        if line.startswith("PIXEL:"):
            r, g, b, a = (int(p) for p in line[6:].split(","))
            return f"#{r:02x}{g:02x}{b:02x} (r={r}, g={g}, b={b}, a={a})"
    return "No pixel data returned"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def get_composite_rect(
    filename: Annotated[str, Field(description="Path to the Aseprite file to read")],
    x: Annotated[
        int, Field(description="Top-left x coordinate of the region (sprite-global)")
    ],
    y: Annotated[
        int, Field(description="Top-left y coordinate of the region (sprite-global)")
    ],
    width: Annotated[
        int, Field(description="Width of the region in pixels; must be > 0")
    ],
    height: Annotated[
        int, Field(description="Height of the region in pixels; must be > 0")
    ],
    frame_index: Annotated[
        int, Field(description="Frame index to read, starting at 1")
    ] = 1,
) -> str:
    """Read VISIBLE RGBA over a rectangle (flattened composite of all layers).

    The rectangular counterpart of get_composite_pixel — reads the composited
    pixels every visible layer produces, not a single cel.

    Returns:
        JSON array of {x, y, hex, r, g, b, a} objects

    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    x_end, y_end = x + width - 1, y + height - 1
    script = f"""
    {_FLATTEN_FRAME}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end
    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end
    local clone = Sprite(spr)
    clone:flatten()
    local img = flatten_frame(clone, idx, nil)
    local iw, ih = img.width, img.height
    for py = {y}, {y_end} do
        for px = {x}, {x_end} do
            local r, g, b, a = 0, 0, 0, 0
            if px >= 0 and py >= 0 and px < iw and py < ih then
                local pv = img:getPixel(px, py)
                r = app.pixelColor.rgbaR(pv)
                g = app.pixelColor.rgbaG(pv)
                b = app.pixelColor.rgbaB(pv)
                a = app.pixelColor.rgbaA(pv)
            end
            print(string.format("PIXEL:%d,%d,%d,%d,%d,%d", px, py, r, g, b, a))
        end
    end
    """

    success, output = AsepriteCommand.execute_lua_script(script, filename)
    if not success:
        return f"Failed to read composite pixels: {output}"
    pixels = []
    for line in output.splitlines():
        if line.startswith("ERROR:"):
            return f"Failed to read composite pixels: {line[6:]}"
        if line.startswith("PIXEL:"):
            px, py, r, g, b, a = (int(p) for p in line[6:].split(","))
            pixels.append(
                {
                    "x": px,
                    "y": py,
                    "hex": f"#{r:02x}{g:02x}{b:02x}",
                    "r": r,
                    "g": g,
                    "b": b,
                    "a": a,
                }
            )
    if not pixels:
        return "No pixel data returned"
    return json.dumps(pixels)
