import json
from pathlib import Path
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from ..core.paths import path_exists

_ONION_SCALE_MAX = 64
_MAX_OPACITY = 255


def _validate_onion_skin_params(
    scale: int, ghost_opacity: int, before: int, after: int
) -> str | None:
    """Check onion-skin render params; return an error string or None."""
    if scale < 1 or scale > _ONION_SCALE_MAX:
        return f"scale must be between 1 and {_ONION_SCALE_MAX}"
    if not (0 <= ghost_opacity <= _MAX_OPACITY):
        return f"ghost_opacity must be between 0 and {_MAX_OPACITY}"
    if before < 0 or after < 0:
        return "before and after must be >= 0"
    return None


# Render a frame of the (cloned, flattened) sprite into a canvas-sized
# RGB image. Used by the analysis tools so layer offsets and trimmed
# cels do not skew results.
_FLATTEN_FRAME = """
local function flatten_frame(clone, frame_idx, bg)
    local layer = clone.layers[#clone.layers]
    local img = Image(clone.width, clone.height, ColorMode.RGB)
    if bg then
        for py = 0, img.height - 1 do
            for px = 0, img.width - 1 do
                img:putPixel(px, py, bg)
            end
        end
    end
    local cel = layer:cel(clone.frames[frame_idx])
    if cel then
        img:drawImage(cel.image, cel.position)
    end
    return img
end
"""


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def render_onion_skin(
    filename: Annotated[str, Field(description="Aseprite file to read")],
    frame_index: Annotated[int, Field(description="Frame to render, starting at 1")],
    output_filename: Annotated[str, Field(description="Output PNG path")],
    before: Annotated[
        int, Field(description="Number of previous frames to ghost (default 1)")
    ] = 1,
    after: Annotated[
        int, Field(description="Number of following frames to ghost (default 1)")
    ] = 1,
    scale: Annotated[
        int, Field(description="Integer nearest-neighbor scale factor (default 4)")
    ] = 4,
    ghost_opacity: Annotated[
        int, Field(description="Opacity of ghost frames, 0-255 (default 100)")
    ] = 100,
) -> str:
    """Render a frame with neighboring frames as translucent onion-skin ghosts.

    Produces a PNG of the given frame composited over ghosted copies of
    the surrounding frames — the batch-mode equivalent of Aseprite's
    onion skinning. Essential for checking motion continuity while
    animating: export it, open the PNG, and verify the in-between
    positions line up. The source .aseprite file is only read, never
    modified; the render is written to output_filename.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    param_err = _validate_onion_skin_params(scale, ghost_opacity, before, after)
    if param_err:
        return param_err
    err = reject_traversal(output_filename)
    if err:
        return err
    if not output_filename.lower().endswith(".png"):
        output_filename = f"{output_filename}.png"

    safe_out = lua_escape(str(Path(output_filename).resolve()).replace("\\", "/"))
    script = f"""
    {_FLATTEN_FRAME}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local clone = Sprite(spr)
    clone:flatten()

    local white = app.pixelColor.rgba(255, 255, 255, 255)
    local comp = Image(clone.width, clone.height, ColorMode.RGB)
    for py = 0, comp.height - 1 do
        for px = 0, comp.width - 1 do
            comp:putPixel(px, py, white)
        end
    end

    -- Ghosts: oldest first so closer frames draw on top
    for offset = {before}, 1, -1 do
        local fi = idx - offset
        if fi >= 1 then
            comp:drawImage(flatten_frame(clone, fi, nil), Point(0, 0), {ghost_opacity}, BlendMode.NORMAL)
        end
    end
    for offset = {after}, 1, -1 do
        local fi = idx + offset
        if fi <= #clone.frames then
            comp:drawImage(flatten_frame(clone, fi, nil), Point(0, 0), {ghost_opacity}, BlendMode.NORMAL)
        end
    end
    comp:drawImage(flatten_frame(clone, idx, nil), Point(0, 0), 255, BlendMode.NORMAL)

    local s = {scale}
    local big = Image(comp.width * s, comp.height * s, ColorMode.RGB)
    for py = 0, comp.height - 1 do
        for px = 0, comp.width - 1 do
            local v = comp:getPixel(px, py)
            for oy = 0, s - 1 do
                for ox = 0, s - 1 do
                    big:putPixel(px * s + ox, py * s + oy, v)
                end
            end
        end
    end

    big:saveAs("{safe_out}")
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Onion-skin render of frame {frame_index} "
            f"(-{before}/+{after} ghosts) saved to {output_filename} at {scale}x"
        )
    return f"Failed to render onion skin: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def compare_frames(
    filename: Annotated[str, Field(description="Aseprite file to read")],
    frame_a: Annotated[int, Field(description="First frame index, starting at 1")],
    frame_b: Annotated[int, Field(description="Second frame index, starting at 1")],
) -> str:
    """Compare two frames and report how much they differ.

    Flattens the sprite (non-destructively) and diffs the two frames
    pixel by pixel. Use while animating to confirm a frame actually
    changed, or that it did not change too much.

    Returns:
        JSON with changed pixel count, total pixels, percent changed,
        and the bounding box of the changed region.

    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    script = f"""
    {_FLATTEN_FRAME}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local a = {frame_a}
    local b = {frame_b}
    if a < 1 or a > #spr.frames or b < 1 or b > #spr.frames then
        print("ERROR:Frame index out of range") return
    end

    local clone = Sprite(spr)
    clone:flatten()

    local img_a = flatten_frame(clone, a, nil)
    local img_b = flatten_frame(clone, b, nil)

    local changed = 0
    local min_x, min_y = math.huge, math.huge
    local max_x, max_y = -1, -1
    for py = 0, img_a.height - 1 do
        for px = 0, img_a.width - 1 do
            local va = img_a:getPixel(px, py)
            local vb = img_b:getPixel(px, py)
            local aa = app.pixelColor.rgbaA(va)
            local ab = app.pixelColor.rgbaA(vb)
            local diff
            if aa == 0 and ab == 0 then
                diff = false
            else
                diff = va ~= vb
            end
            if diff then
                changed = changed + 1
                if px < min_x then min_x = px end
                if py < min_y then min_y = py end
                if px > max_x then max_x = px end
                if py > max_y then max_y = py end
            end
        end
    end

    if changed == 0 then
        -- math.huge has no integer representation for %d
        min_x, min_y, max_x, max_y = 0, 0, -1, -1
    end
    print(string.format("DIFF:%d,%d,%d,%d,%d,%d,%d",
        changed, img_a.width * img_a.height, min_x, min_y, max_x, max_y,
        (changed > 0) and 1 or 0))
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to compare frames: {output}"

    for line in output.splitlines():
        if line.startswith("DIFF:"):
            parts = [int(p) for p in line[len("DIFF:") :].split(",")]
            changed, total, min_x, min_y, max_x, max_y, any_change = parts
            result: dict[str, object] = {
                "frame_a": frame_a,
                "frame_b": frame_b,
                "changed_pixels": changed,
                "total_pixels": total,
                "percent_changed": round(changed / total * 100, 2) if total else 0,
            }
            if any_change:
                result["changed_bounds"] = {
                    "x": min_x,
                    "y": min_y,
                    "width": max_x - min_x + 1,
                    "height": max_y - min_y + 1,
                }
            return json.dumps(result)
    return "No diff data returned"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def get_color_stats(
    filename: Annotated[str, Field(description="Aseprite file to read")],
    frame_index: Annotated[
        int, Field(description="Frame to analyze, starting at 1 (default 1)")
    ] = 1,
    top: Annotated[
        int, Field(description="How many of the most-used colors to list (default 16)")
    ] = 16,
) -> str:
    """Report the colors used in a frame and how often each appears.

    Flattens the sprite (non-destructively) and histograms the frame.
    Use to check palette discipline: too many near-duplicate colors is
    a common pixel-art mistake.

    Returns:
        JSON with unique color count, opaque pixel count, and the top
        colors with usage counts.

    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if top < 1:
        return "top must be >= 1"

    script = f"""
    {_FLATTEN_FRAME}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local clone = Sprite(spr)
    clone:flatten()
    local img = flatten_frame(clone, idx, nil)

    local counts = {{}}
    local opaque = 0
    for py = 0, img.height - 1 do
        for px = 0, img.width - 1 do
            local v = img:getPixel(px, py)
            if app.pixelColor.rgbaA(v) > 0 then
                opaque = opaque + 1
                local hex = string.format("#%02X%02X%02X",
                    app.pixelColor.rgbaR(v),
                    app.pixelColor.rgbaG(v),
                    app.pixelColor.rgbaB(v))
                counts[hex] = (counts[hex] or 0) + 1
            end
        end
    end

    local unique = 0
    for hex, count in pairs(counts) do
        unique = unique + 1
        print("COLOR:" .. hex .. "," .. count)
    end
    print("OPAQUE:" .. opaque)
    print("UNIQUE:" .. unique)
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to get color stats: {output}"

    colors: list[dict[str, str | int]] = []
    opaque = 0
    unique = 0
    for line in output.splitlines():
        if line.startswith("COLOR:"):
            hex_color, count = line[len("COLOR:") :].split(",")
            colors.append({"color": hex_color, "count": int(count)})
        elif line.startswith("OPAQUE:"):
            opaque = int(line[len("OPAQUE:") :])
        elif line.startswith("UNIQUE:"):
            unique = int(line[len("UNIQUE:") :])

    colors.sort(key=lambda c: int(c["count"]), reverse=True)
    return json.dumps(
        {
            "frame": frame_index,
            "unique_colors": unique,
            "opaque_pixels": opaque,
            "top_colors": colors[:top],
        }
    )
