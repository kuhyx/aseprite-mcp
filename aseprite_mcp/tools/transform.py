from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.commands import AsepriteCommand, lua_escape
from ..core.lua import FIND_LAYER
from ..core.paths import path_exists


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def flip_layer(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Layer name to flip")],
    frame_index: Annotated[int, Field(description="Frame index starting at 1")],
    direction: Annotated[
        str, Field(description='"horizontal" or "vertical"')
    ] = "horizontal",
) -> str:
    """Flip a layer's image horizontally or vertically."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if direction not in ("horizontal", "vertical"):
        return "direction must be 'horizontal' or 'vertical'"

    safe_layer = lua_escape(layer_name)
    flip_h = "true" if direction == "horizontal" else "false"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end

    local cel = target:cel(spr.frames[idx])
    if not cel then print("ERROR:No cel at that layer/frame") return end

    app.transaction(function()
        local img = cel.image
        local w = img.width
        local h = img.height
        local flip_horizontal = {flip_h}

        local pixels = {{}}
        for py = 0, h - 1 do
            pixels[py] = {{}}
            for px = 0, w - 1 do
                pixels[py][px] = img:getPixel(px, py)
            end
        end

        for py = 0, h - 1 do
            for px = 0, w - 1 do
                if flip_horizontal then
                    img:putPixel(px, py, pixels[py][w - 1 - px])
                else
                    img:putPixel(px, py, pixels[h - 1 - py][px])
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Layer '{layer_name}' flipped {direction}ly in {filename}"
    return f"Failed to flip layer: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def rotate_layer(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Layer name to rotate")],
    frame_index: Annotated[int, Field(description="Frame index starting at 1")],
    angle: Annotated[
        int, Field(description="Rotation angle: 90, 180, or 270 (clockwise)")
    ] = 90,
) -> str:
    """Rotate a layer's image 90, 180, or 270 degrees clockwise."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if angle not in (90, 180, 270):
        return "angle must be 90, 180, or 270"

    safe_layer = lua_escape(layer_name)

    if angle == 180:
        rotate_lua = """
        local w = img.width
        local h = img.height
        local pixels = {}
        for py = 0, h - 1 do
            pixels[py] = {}
            for px = 0, w - 1 do
                pixels[py][px] = img:getPixel(px, py)
            end
        end
        for py = 0, h - 1 do
            for px = 0, w - 1 do
                img:putPixel(px, py, pixels[h - 1 - py][w - 1 - px])
            end
        end
        """
    elif angle == 90:
        # 90° clockwise: (px, py) → (old_h-1-py, px) in new image (new_w=old_h, new_h=old_w)
        rotate_lua = """
        local old_w = img.width
        local old_h = img.height
        local new_img = Image(old_h, old_w, img.colorMode)
        for py = 0, old_h - 1 do
            for px = 0, old_w - 1 do
                new_img:putPixel(old_h - 1 - py, px, img:getPixel(px, py))
            end
        end
        cel.image = new_img
        """
    else:
        # 270° clockwise (= 90° CCW): (px, py) → (py, old_w-1-px) in new image (new_w=old_h, new_h=old_w)
        rotate_lua = """
        local old_w = img.width
        local old_h = img.height
        local new_img = Image(old_h, old_w, img.colorMode)
        for py = 0, old_h - 1 do
            for px = 0, old_w - 1 do
                new_img:putPixel(py, old_w - 1 - px, img:getPixel(px, py))
            end
        end
        cel.image = new_img
        """

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer}")
    if not target then print("ERROR:Layer not found") return end

    local cel = target:cel(spr.frames[idx])
    if not cel then print("ERROR:No cel at that layer/frame") return end

    app.transaction(function()
        local img = cel.image
        {rotate_lua}
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Layer '{layer_name}' rotated {angle}° clockwise in {filename}"
    return f"Failed to rotate layer: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def resize_canvas(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    width: Annotated[int, Field(description="New canvas width in pixels")],
    height: Annotated[int, Field(description="New canvas height in pixels")],
) -> str:
    """Scale the canvas and all its content to new dimensions."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        spr:resize({width}, {height})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Canvas resized to {width}x{height} in {filename}"
    return f"Failed to resize canvas: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def crop_canvas(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    x: Annotated[int, Field(description="Left edge of the crop area")],
    y: Annotated[int, Field(description="Top edge of the crop area")],
    width: Annotated[int, Field(description="Width of the crop area")],
    height: Annotated[int, Field(description="Height of the crop area")],
) -> str:
    """Crop the canvas to the given rectangle, discarding content outside it."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    if {x} >= spr.width or {y} >= spr.height or {x} + {width} <= 0 or {y} + {height} <= 0 then
        print("ERROR:Crop rect is fully outside the canvas") return
    end

    app.transaction(function()
        spr:crop({x}, {y}, {width}, {height})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Canvas cropped to ({x},{y}) {width}x{height} in {filename}"
    return f"Failed to crop canvas: {output}"
