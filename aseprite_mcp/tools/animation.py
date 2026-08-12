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
async def add_frames(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    count: Annotated[int, Field(description="Number of frames to add")],
    duration_ms: Annotated[
        int | None,
        Field(description="Optional duration for each new frame in milliseconds"),
    ] = None,
) -> str:
    """Add multiple frames to a sprite and optionally set their duration."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    if count < 1:
        return "Count must be >= 1"

    duration_line = ""
    if duration_ms is not None and duration_ms > 0:
        duration_line = f"spr.frames[#spr.frames].duration = {duration_ms} / 1000.0"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        for i = 1, {count} do
            spr:newFrame()
            {duration_line}
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Added {count} frames to {filename}"
    return f"Failed to add frames: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_frame_duration_all(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    duration_ms: Annotated[
        int, Field(description="Duration to apply to every frame, in milliseconds")
    ],
) -> str:
    """Set the duration of all frames in milliseconds."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if duration_ms <= 0:
        return "Duration must be > 0"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        for i = 1, #spr.frames do
            spr.frames[i].duration = {duration_ms} / 1000.0
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Set duration of all frames to {duration_ms}ms in {filename}"
    return f"Failed to set frame durations: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_layer_visibility(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to target")],
    visible: Annotated[
        bool,
        Field(description="Whether the layer should be shown (True) or hidden (False)"),
    ] = True,
) -> str:
    """Set layer visibility by name."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    visible_flag = "true" if visible else "false"
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    app.transaction(function()
        target.isVisible = {visible_flag}
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Layer '{layer_name}' visibility set to {visible} in {filename}"
    return f"Failed to set layer visibility: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_layer_opacity(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the layer to target")],
    opacity: Annotated[
        int,
        Field(
            description="Opacity value from 0 (fully transparent) to 255 (fully opaque)"
        ),
    ],
) -> str:
    """Set layer opacity by name (0-255)."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if opacity < 0 or opacity > 255:
        return "Opacity must be between 0 and 255"

    safe_layer_name = lua_escape(layer_name)
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    app.transaction(function()
        target.opacity = {opacity}
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Layer '{layer_name}' opacity set to {opacity} in {filename}"
    return f"Failed to set layer opacity: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def get_sprite_info(
    filename: Annotated[str, Field(description="Name of the Aseprite file to inspect")],
) -> str:
    """Return sprite info as JSON string (size, color mode, frame durations, layers, tags)."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    # NOTE: batch mode discards Lua `return` values — output MUST go through print().
    script = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local cm = "unknown"
    if spr.colorMode == ColorMode.RGB then cm = "rgb"
    elseif spr.colorMode == ColorMode.INDEXED then cm = "indexed"
    elseif spr.colorMode == ColorMode.GRAY then cm = "gray" end

    local parts = {}
    table.insert(parts, "{")
    table.insert(parts, "\\"width\\":" .. spr.width .. ",")
    table.insert(parts, "\\"height\\":" .. spr.height .. ",")
    table.insert(parts, "\\"color_mode\\":\\"" .. cm .. "\\",")
    table.insert(parts, "\\"frames\\":" .. #spr.frames .. ",")
    table.insert(parts, "\\"durations_ms\\":[")
    for i, frame in ipairs(spr.frames) do
        table.insert(parts, tostring(math.floor(frame.duration * 1000 + 0.5)))
        if i < #spr.frames then table.insert(parts, ",") end
    end
    table.insert(parts, "],")
    table.insert(parts, "\\"layers\\":[")
    -- Recurse into groups so nested layers are enumerated too; each entry
    -- carries its immediate parent group name (null at top level).
    local first_layer = true
    local function walk_layers(layers, parent)
        for _, layer in ipairs(layers) do
            if not first_layer then table.insert(parts, ",") end
            first_layer = false
            local pj = "null"
            if parent then pj = string.format("%q", parent) end
            local entry = "{\\"name\\":" .. string.format("%q", layer.name) .. ",\\"visible\\":" .. tostring(layer.isVisible) .. ",\\"opacity\\":" .. (layer.opacity or 255) .. ",\\"is_group\\":" .. tostring(layer.isGroup) .. ",\\"parent\\":" .. pj .. "}"
            table.insert(parts, entry)
            if layer.isGroup then walk_layers(layer.layers, layer.name) end
        end
    end
    walk_layers(spr.layers, nil)
    table.insert(parts, "],")
    local dirs = {[0]="forward", "reverse", "pingpong", "pingpong_reverse"}
    table.insert(parts, "\\"tags\\":[")
    for i, t in ipairs(spr.tags) do
        local entry = "{\\"name\\":" .. string.format("%q", t.name) .. ",\\"from\\":" .. t.fromFrame.frameNumber .. ",\\"to\\":" .. t.toFrame.frameNumber .. ",\\"direction\\":\\"" .. (dirs[tonumber(t.aniDir)] or tostring(t.aniDir)) .. "\\"}"
        table.insert(parts, entry)
        if i < #spr.tags then table.insert(parts, ",") end
    end
    table.insert(parts, "]}")
    print(table.concat(parts))
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return output
    return f"Failed to get sprite info: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def duplicate_frame_range(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    start_frame: Annotated[
        int,
        Field(description="Starting frame index of the range to duplicate (1-based)"),
    ],
    end_frame: Annotated[
        int,
        Field(
            description="Ending frame index of the range to duplicate (1-based, inclusive)"
        ),
    ],
    times: Annotated[
        int,
        Field(description="Number of times to append the duplicated range to the end"),
    ] = 1,
) -> str:
    """Duplicate a frame range and append copies to the end."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if times < 1:
        return "Times must be >= 1"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    local times = {times}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end
    if times < 1 then print("ERROR:Times must be >= 1") return end

    app.transaction(function()
        for t = 1, times do
            for fi = start_idx, end_idx do
                app.activeFrame = spr.frames[#spr.frames]
                local new_frame = spr:newFrame()
                for _, layer in ipairs(spr.layers) do
                    if not layer.isGroup then
                        local cel = layer:cel(spr.frames[fi])
                        if cel then
                            local img = cel.image:clone()
                            spr:newCel(layer, new_frame, img, cel.position)
                        end
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
        return f"Duplicated frames {start_frame}-{end_frame} (x{times}) in {filename}"
    return f"Failed to duplicate frame range: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_cel_position(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cel")
    ],
    frame_index: Annotated[
        int, Field(description="Frame index of the cel to move (1-based)")
    ],
    x: Annotated[int, Field(description="New X position of the cel, in pixels")],
    y: Annotated[int, Field(description="New Y position of the cel, in pixels")],
    create_if_missing: Annotated[
        bool,
        Field(
            description="If the cel does not exist yet, create it instead of failing"
        ),
    ] = False,
    source_frame_index: Annotated[
        int | None,
        Field(
            description=(
                "When creating a missing cel, the frame index to copy its image from "
                "(defaults to frame_index itself, producing an empty image if that also has no cel)"
            )
        ),
    ] = None,
) -> str:
    """Set a cel's position in a specific layer and frame."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    source_idx = "nil" if source_frame_index is None else str(source_frame_index)
    create_flag = "true" if create_if_missing else "false"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target_layer = find_layer(spr, "{safe_layer_name}")
    if not target_layer then print("ERROR:Layer not found") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then
        print("ERROR:Frame index out of range") return
    end

    app.transaction(function()
        local frame = spr.frames[idx]
        local cel = target_layer:cel(frame)
        if not cel and {create_flag} then
            local source_frame = {source_idx}
            if source_frame == nil then
                source_frame = idx
            end
            if source_frame < 1 or source_frame > #spr.frames then
                return
            end
            local source_cel = target_layer:cel(spr.frames[source_frame])
            if source_cel then
                local img = source_cel.image:clone()
                cel = spr:newCel(target_layer, frame, img, source_cel.position)
            else
                local img = Image(spr.width, spr.height, spr.colorMode)
                cel = spr:newCel(target_layer, frame, img, Point(0, 0))
            end
        end
        if not cel then return end
        cel.position = Point({x}, {y})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Cel position set to ({x}, {y}) on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to set cel position: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def tween_cel_positions(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cels to move")
    ],
    start_frame: Annotated[
        int, Field(description="Starting frame index of the tween range (1-based)")
    ],
    end_frame: Annotated[
        int,
        Field(description="Ending frame index of the tween range (1-based, inclusive)"),
    ],
    start_x: Annotated[int, Field(description="X position at start_frame, in pixels")],
    start_y: Annotated[int, Field(description="Y position at start_frame, in pixels")],
    end_x: Annotated[int, Field(description="X position at end_frame, in pixels")],
    end_y: Annotated[int, Field(description="Y position at end_frame, in pixels")],
    create_missing_cels: Annotated[
        bool,
        Field(
            description="Create a cel on frames in the range that don't already have one"
        ),
    ] = False,
    source_frame_index: Annotated[
        int | None,
        Field(
            description=(
                "When creating a missing cel, the frame index to copy its image from "
                "(defaults to start_frame)"
            )
        ),
    ] = None,
) -> str:
    """Tween cel positions linearly across a frame range.

    Constant-speed interpolation between (start_x, start_y) and (end_x, end_y).
    For eased motion (ease-in/out, smoothstep), use tween_cel_positions_eased
    instead.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_missing_cels else "false"
    source_idx = "nil" if source_frame_index is None else str(source_frame_index)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target_layer = find_layer(spr, "{safe_layer_name}")
    if not target_layer then print("ERROR:Layer not found") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    local span = end_idx - start_idx
    app.transaction(function()
        for fi = start_idx, end_idx do
            local t = 0
            if span > 0 then
                t = (fi - start_idx) / span
            end
            local x = math.floor({start_x} + ({end_x} - {start_x}) * t + 0.5)
            local y = math.floor({start_y} + ({end_y} - {start_y}) * t + 0.5)
            local frame = spr.frames[fi]
            local cel = target_layer:cel(frame)
            if not cel and {create_flag} then
                local source_frame = {source_idx}
                if source_frame == nil then
                    source_frame = start_idx
                end
                local source_cel = target_layer:cel(spr.frames[source_frame])
                if source_cel then
                    local img = source_cel.image:clone()
                    cel = spr:newCel(target_layer, frame, img, source_cel.position)
                else
                    local img = Image(spr.width, spr.height, spr.colorMode)
                    cel = spr:newCel(target_layer, frame, img, Point(0, 0))
                end
            end
            if cel then
                cel.position = Point(x, y)
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Tweened cel positions on '{layer_name}' frames {start_frame}-{end_frame} in {filename}"
    return f"Failed to tween cel positions: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def offset_cel_positions(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cels to shift")
    ],
    start_frame: Annotated[
        int, Field(description="Starting frame index of the range to offset (1-based)")
    ],
    end_frame: Annotated[
        int,
        Field(
            description="Ending frame index of the range to offset (1-based, inclusive)"
        ),
    ],
    dx: Annotated[
        int,
        Field(description="Amount to add to each cel's current X position, in pixels"),
    ],
    dy: Annotated[
        int,
        Field(description="Amount to add to each cel's current Y position, in pixels"),
    ],
) -> str:
    """Offset cel positions by a delta across a frame range."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target_layer = find_layer(spr, "{safe_layer_name}")
    if not target_layer then print("ERROR:Layer not found") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    app.transaction(function()
        for fi = start_idx, end_idx do
            local frame = spr.frames[fi]
            local cel = target_layer:cel(frame)
            if cel then
                local pos = cel.position
                cel.position = Point(pos.x + {dx}, pos.y + {dy})
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Offset cel positions by ({dx}, {dy}) on '{layer_name}' frames {start_frame}-{end_frame} in {filename}"
    return f"Failed to offset cel positions: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def create_cel(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer to create the cel on")
    ],
    frame_index: Annotated[
        int, Field(description="Frame index to create the cel at (1-based)")
    ],
    x: Annotated[int, Field(description="X position of the new cel, in pixels")] = 0,
    y: Annotated[int, Field(description="Y position of the new cel, in pixels")] = 0,
) -> str:
    """Create an empty cel on a layer/frame.

    Does nothing if a cel already exists at that layer/frame — use
    set_cel_position or copy_cel to modify an existing cel instead.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    app.transaction(function()
        local frame = spr.frames[idx]
        local cel = target:cel(frame)
        if cel then return end
        local img = Image(spr.width, spr.height, spr.colorMode)
        spr:newCel(target, frame, img, Point({x}, {y}))
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Cel created on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to create cel: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def clear_cel(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cel")
    ],
    frame_index: Annotated[
        int, Field(description="Frame index of the cel to delete (1-based)")
    ],
) -> str:
    """Delete a cel on a layer/frame. A no-op if no cel exists there already."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    app.transaction(function()
        local frame = spr.frames[idx]
        local cel = target:cel(frame)
        if cel then
            spr:deleteCel(cel)
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Cel cleared on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to clear cel: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def copy_cel(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing both cels")
    ],
    source_frame: Annotated[
        int, Field(description="Frame index to copy the cel from (1-based)")
    ],
    target_frame: Annotated[
        int, Field(description="Frame index to copy the cel to (1-based)")
    ],
    replace: Annotated[
        bool,
        Field(
            description="If the target frame already has a cel, delete it and replace with the copy"
        ),
    ] = True,
) -> str:
    """Copy a cel from one frame to another.

    Scope: a single layer, a single source frame, a single target frame.
    For copying every layer's cel from one frame to another, use
    copy_frame; for copying to a range of frames, use propagate_cels
    (specific layers) or propagate_frame_to_range (all layers).
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    replace_flag = "true" if replace else "false"
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local src_idx = {source_frame}
    local dst_idx = {target_frame}
    if src_idx < 1 or src_idx > #spr.frames then print("ERROR:Source frame out of range") return end
    if dst_idx < 1 or dst_idx > #spr.frames then print("ERROR:Target frame out of range") return end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    app.transaction(function()
        local src = target:cel(spr.frames[src_idx])
        if not src then return end
        local dst = target:cel(spr.frames[dst_idx])
        if dst and {replace_flag} then
            spr:deleteCel(dst)
            dst = nil
        end
        if not dst then
            local img = src.image:clone()
            spr:newCel(target, spr.frames[dst_idx], img, src.position)
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Cel copied on '{layer_name}' from frame {source_frame} to {target_frame} in {filename}"
    return f"Failed to copy cel: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def copy_frame(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    source_frame: Annotated[
        int, Field(description="Frame index to copy all layer cels from (1-based)")
    ],
    target_frame: Annotated[
        int | None,
        Field(
            description="Frame index to copy into; if omitted, a new frame is appended and copied into"
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        Field(
            description="If the target frame already has cels, delete them before copying in the new ones"
        ),
    ] = True,
) -> str:
    """Copy all cels from a source frame to a target frame (or append).

    Scope: every layer, a single source frame, a single target frame (or a
    freshly appended one). For a single layer only, use copy_cel; for a
    range of target frames, use propagate_frame_to_range.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    overwrite_flag = "true" if overwrite else "false"
    target_idx = "nil" if target_frame is None else str(target_frame)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local src_idx = {source_frame}
    if src_idx < 1 or src_idx > #spr.frames then print("ERROR:Source frame out of range") return end

    local dst_idx = {target_idx}
    app.transaction(function()
        local dst_frame = nil
        if dst_idx == nil then
            dst_frame = spr:newFrame()
        else
            if dst_idx < 1 or dst_idx > #spr.frames then return end
            dst_frame = spr.frames[dst_idx]
            if {overwrite_flag} then
                for _, layer in ipairs(spr.layers) do
                    if not layer.isGroup then
                        local cel = layer:cel(dst_frame)
                        if cel then spr:deleteCel(cel) end
                    end
                end
            end
        end

        for _, layer in ipairs(spr.layers) do
            if not layer.isGroup then
                local cel = layer:cel(spr.frames[src_idx])
                if cel then
                    local img = cel.image:clone()
                    spr:newCel(layer, dst_frame, img, cel.position)
                end
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        if target_frame is None:
            return f"Frame {source_frame} copied to new frame in {filename}"
        return f"Frame {source_frame} copied to frame {target_frame} in {filename}"
    return f"Failed to copy frame: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def propagate_frame_to_range(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    source_frame: Annotated[
        int, Field(description="Frame index to copy every layer's cel from (1-based)")
    ],
    start_frame: Annotated[
        int, Field(description="Start of the destination frame range (1-based)")
    ],
    end_frame: Annotated[
        int,
        Field(description="End of the destination frame range (1-based, inclusive)"),
    ],
    overwrite: Annotated[
        bool,
        Field(
            description="Delete each destination frame's existing cels before copying in the new ones"
        ),
    ] = True,
) -> str:
    """Copy all layers from a source frame to a range of frames.

    Scope: every layer, a single source frame, a range of target frames.
    For only specific layers, use propagate_cels; for a single target
    frame, use copy_frame.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    overwrite_flag = "true" if overwrite else "false"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local src_idx = {source_frame}
    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if src_idx < 1 or src_idx > #spr.frames then print("ERROR:Source frame out of range") return end
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    app.transaction(function()
        for fi = start_idx, end_idx do
            if fi ~= src_idx then
                local dst_frame = spr.frames[fi]
                if {overwrite_flag} then
                    for _, layer in ipairs(spr.layers) do
                        if not layer.isGroup then
                            local dst_cel = layer:cel(dst_frame)
                            if dst_cel then spr:deleteCel(dst_cel) end
                        end
                    end
                end
                for _, layer in ipairs(spr.layers) do
                    if not layer.isGroup then
                        local src_cel = layer:cel(spr.frames[src_idx])
                        if src_cel then
                            local img = src_cel.image:clone()
                            spr:newCel(layer, dst_frame, img, src_cel.position)
                        end
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
        return (
            f"Propagated frame {source_frame} to frames {start_frame}-{end_frame} "
            f"in {filename}"
        )
    return f"Failed to propagate frame range: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_tag(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    name: Annotated[
        str,
        Field(
            description="Tag name; creates a new tag or updates the existing tag with this name"
        ),
    ],
    from_frame: Annotated[
        int, Field(description="First frame index covered by the tag (1-based)")
    ],
    to_frame: Annotated[
        int,
        Field(description="Last frame index covered by the tag (1-based, inclusive)"),
    ],
    direction: Annotated[
        str,
        Field(
            description=(
                "Playback direction for the tag: one of "
                "'forward', 'reverse', 'pingpong', 'pingpong_reverse'"
            )
        ),
    ] = "forward",
) -> str:
    """Create or update an animation tag on the sprite."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    ani_dirs = {
        "forward": "AniDir.FORWARD",
        "reverse": "AniDir.REVERSE",
        "pingpong": "AniDir.PING_PONG",
        "pingpong_reverse": "AniDir.PING_PONG_REVERSE",
    }
    if direction not in ani_dirs:
        return f"Unsupported direction '{direction}' (forward, reverse, pingpong, pingpong_reverse)"

    safe_name = lua_escape(name)
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local start_idx = {from_frame}
    local end_idx = {to_frame}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    local tag = nil
    for _, t in ipairs(spr.tags) do
        if t.name == "{safe_name}" then tag = t break end
    end
    if not tag then
        tag = spr:newTag(start_idx, end_idx)
    else
        tag.fromFrame = spr.frames[start_idx]
        tag.toFrame = spr.frames[end_idx]
    end
    tag.name = "{safe_name}"
    tag.aniDir = {ani_dirs[direction]}

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Tag '{name}' set to frames {from_frame}-{to_frame} (direction={direction}) in {filename}"
    return f"Failed to set tag: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_onion_skin(
    filename: Annotated[
        str, Field(description="Name of the Aseprite file to check exists")
    ],
    enabled: Annotated[
        bool, Field(description="Whether onion skinning would be enabled")
    ] = True,
    before: Annotated[
        int,
        Field(
            description="Number of previous frames that would be shown as onion skin"
        ),
    ] = 2,
    after: Annotated[
        int,
        Field(
            description="Number of following frames that would be shown as onion skin"
        ),
    ] = 2,
    opacity: Annotated[
        int, Field(description="Onion skin overlay opacity from 0 to 255")
    ] = 128,
) -> str:
    """Report the requested onion skin configuration without applying it.

    Onion skin is a UI-only preference in Aseprite's batch (headless) mode:
    there is no scriptable API to persist it, so this tool validates the
    arguments and echoes them back but makes no change to the file. It
    exists so callers get a clear, structured non-error instead of a
    confusing failure when they ask for onion skin settings.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if before < 0 or after < 0:
        return "Before/after must be >= 0"
    if opacity < 0 or opacity > 255:
        return "Opacity must be between 0 and 255"

    return (
        "Onion skin settings are UI-only in batch mode; no changes applied "
        f"(enabled={enabled}, before={before}, after={after}, opacity={opacity})"
    )


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def propagate_cels(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_names: Annotated[
        list[str], Field(description="Names of the layers whose cels should be copied")
    ],
    source_frame: Annotated[
        int, Field(description="Frame index to copy each layer's cel from (1-based)")
    ],
    start_frame: Annotated[
        int, Field(description="Start of the destination frame range (1-based)")
    ],
    end_frame: Annotated[
        int,
        Field(description="End of the destination frame range (1-based, inclusive)"),
    ],
    replace: Annotated[
        bool,
        Field(description="Delete each destination cel before copying in the new one"),
    ] = True,
) -> str:
    """Copy cels from a source frame to a range of frames for specific layers.

    Scope: only the named layers, a single source frame, a range of target
    frames. For all layers, use propagate_frame_to_range; for a single
    target frame, use copy_cel.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not layer_names:
        return "Layer names list cannot be empty"

    replace_flag = "true" if replace else "false"
    layers_lua = "{" + ",".join([f'"{lua_escape(name)}"' for name in layer_names]) + "}"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local src_idx = {source_frame}
    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if src_idx < 1 or src_idx > #spr.frames then print("ERROR:Source frame out of range") return end
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    {FIND_LAYER}
    local name_list = {layers_lua}
    local targets = {{}}
    for _, name in ipairs(name_list) do
        local m = find_layer(spr, name)
        if m then table.insert(targets, m) end
    end
    if #targets == 0 then print("ERROR:No layers found") return end

    app.transaction(function()
        for fi = start_idx, end_idx do
            if fi ~= src_idx then
                local dst_frame = spr.frames[fi]
                for _, layer in ipairs(targets) do
                    local src_cel = layer:cel(spr.frames[src_idx])
                    if src_cel then
                        local dst_cel = layer:cel(dst_frame)
                        if dst_cel and {replace_flag} then
                            spr:deleteCel(dst_cel)
                            dst_cel = nil
                        end
                        if not dst_cel then
                            local img = src_cel.image:clone()
                            spr:newCel(layer, dst_frame, img, src_cel.position)
                        end
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
        return (
            f"Propagated cels from frame {source_frame} to frames {start_frame}-{end_frame} "
            f"for layers {', '.join(layer_names)} in {filename}"
        )
    return f"Failed to propagate cels: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def tween_cel_positions_eased(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cels to move")
    ],
    start_frame: Annotated[
        int, Field(description="Starting frame index of the tween range (1-based)")
    ],
    end_frame: Annotated[
        int,
        Field(description="Ending frame index of the tween range (1-based, inclusive)"),
    ],
    start_x: Annotated[int, Field(description="X position at start_frame, in pixels")],
    start_y: Annotated[int, Field(description="Y position at start_frame, in pixels")],
    end_x: Annotated[int, Field(description="X position at end_frame, in pixels")],
    end_y: Annotated[int, Field(description="Y position at end_frame, in pixels")],
    easing: Annotated[
        str,
        Field(
            description=(
                "Easing curve applied to the tween progress: one of "
                "'linear', 'ease_in', 'ease_out', 'ease_in_out', 'smoothstep'"
            )
        ),
    ] = "smoothstep",
    create_missing_cels: Annotated[
        bool,
        Field(
            description="Create a cel on frames in the range that don't already have one"
        ),
    ] = False,
    source_frame_index: Annotated[
        int | None,
        Field(
            description=(
                "When creating a missing cel, the frame index to copy its image from "
                "(defaults to start_frame)"
            )
        ),
    ] = None,
) -> str:
    """Tween cel positions with easing across a frame range.

    Same as tween_cel_positions but with a non-linear easing curve applied
    to the interpolation, for motion that accelerates/decelerates instead
    of moving at constant speed.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    easing = (easing or "smoothstep").lower().strip()
    if easing not in {"linear", "ease_in", "ease_out", "ease_in_out", "smoothstep"}:
        return "Unsupported easing (linear, ease_in, ease_out, ease_in_out, smoothstep)"

    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_missing_cels else "false"
    source_idx = "nil" if source_frame_index is None else str(source_frame_index)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target_layer = find_layer(spr, "{safe_layer_name}")
    if not target_layer then print("ERROR:Layer not found") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    local function ease(t)
        local mode = "{easing}"
        if mode == "linear" then return t end
        if mode == "ease_in" then return t * t end
        if mode == "ease_out" then return 1 - (1 - t) * (1 - t) end
        if mode == "ease_in_out" then
            if t < 0.5 then return 2 * t * t end
            local u = -2 * t + 2
            return 1 - (u * u) / 2
        end
        return t * t * (3 - 2 * t)
    end

    local span = end_idx - start_idx
    app.transaction(function()
        for fi = start_idx, end_idx do
            local t = 0
            if span > 0 then
                t = (fi - start_idx) / span
            end
            local e = ease(t)
            local x = math.floor({start_x} + ({end_x} - {start_x}) * e + 0.5)
            local y = math.floor({start_y} + ({end_y} - {start_y}) * e + 0.5)
            local frame = spr.frames[fi]
            local cel = target_layer:cel(frame)
            if not cel and {create_flag} then
                local source_frame = {source_idx}
                if source_frame == nil then
                    source_frame = start_idx
                end
                local source_cel = target_layer:cel(spr.frames[source_frame])
                if source_cel then
                    local img = source_cel.image:clone()
                    cel = spr:newCel(target_layer, frame, img, source_cel.position)
                else
                    local img = Image(spr.width, spr.height, spr.colorMode)
                    cel = spr:newCel(target_layer, frame, img, Point(0, 0))
                end
            end
            if cel then
                cel.position = Point(x, y)
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Tweened cel positions ({easing}) on '{layer_name}' frames {start_frame}-{end_frame} "
            f"in {filename}"
        )
    return f"Failed to tween cel positions with easing: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def oscillate_cel_positions(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cels to move")
    ],
    start_frame: Annotated[
        int,
        Field(description="Starting frame index of the range to oscillate (1-based)"),
    ],
    end_frame: Annotated[
        int,
        Field(
            description="Ending frame index of the range to oscillate (1-based, inclusive)"
        ),
    ],
    amplitude_x: Annotated[
        int,
        Field(
            description="Peak horizontal displacement added to each cel's current X, in pixels"
        ),
    ] = 0,
    amplitude_y: Annotated[
        int,
        Field(
            description="Peak vertical displacement added to each cel's current Y, in pixels"
        ),
    ] = 0,
    cycles: Annotated[
        float,
        Field(description="Number of full sine wave cycles spanned by the frame range"),
    ] = 1.0,
    phase_deg: Annotated[
        float,
        Field(description="Phase offset of the sine wave at start_frame, in degrees"),
    ] = 0.0,
    create_missing_cels: Annotated[
        bool,
        Field(
            description="Create a cel on frames in the range that don't already have one"
        ),
    ] = False,
    source_frame_index: Annotated[
        int | None,
        Field(
            description=(
                "When creating a missing cel, the frame index to copy its image from "
                "(defaults to start_frame)"
            )
        ),
    ] = None,
) -> str:
    """Oscillate cel positions across a frame range using a sine wave."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_missing_cels else "false"
    source_idx = "nil" if source_frame_index is None else str(source_frame_index)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target_layer = find_layer(spr, "{safe_layer_name}")
    if not target_layer then print("ERROR:Layer not found") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    local amplitude_x = {amplitude_x}
    local amplitude_y = {amplitude_y}
    local cycles = {cycles}
    local phase = ({phase_deg}) * math.pi / 180
    local span = end_idx - start_idx

    app.transaction(function()
        for fi = start_idx, end_idx do
            local t = 0
            if span > 0 then
                t = (fi - start_idx) / span
            end
            local angle = 2 * math.pi * cycles * t + phase
            local dx = math.floor(amplitude_x * math.sin(angle) + 0.5)
            local dy = math.floor(amplitude_y * math.cos(angle) + 0.5)

            local frame = spr.frames[fi]
            local cel = target_layer:cel(frame)
            if not cel and {create_flag} then
                local source_frame = {source_idx}
                if source_frame == nil then
                    source_frame = start_idx
                end
                local source_cel = target_layer:cel(spr.frames[source_frame])
                if source_cel then
                    local img = source_cel.image:clone()
                    cel = spr:newCel(target_layer, frame, img, source_cel.position)
                else
                    local img = Image(spr.width, spr.height, spr.colorMode)
                    cel = spr:newCel(target_layer, frame, img, Point(0, 0))
                end
            end
            if cel then
                local pos = cel.position
                cel.position = Point(pos.x + dx, pos.y + dy)
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Oscillated cel positions on '{layer_name}' frames {start_frame}-{end_frame} "
            f"in {filename}"
        )
    return f"Failed to oscillate cel positions: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def tween_cel_opacity_eased(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cels to fade")
    ],
    start_frame: Annotated[
        int, Field(description="Starting frame index of the tween range (1-based)")
    ],
    end_frame: Annotated[
        int,
        Field(description="Ending frame index of the tween range (1-based, inclusive)"),
    ],
    start_opacity: Annotated[
        int,
        Field(
            description="Opacity at start_frame, from 0 (transparent) to 255 (opaque)"
        ),
    ],
    end_opacity: Annotated[
        int,
        Field(description="Opacity at end_frame, from 0 (transparent) to 255 (opaque)"),
    ],
    easing: Annotated[
        str,
        Field(
            description=(
                "Easing curve applied to the tween progress: one of "
                "'linear', 'ease_in', 'ease_out', 'ease_in_out', 'smoothstep'"
            )
        ),
    ] = "smoothstep",
    create_missing_cels: Annotated[
        bool,
        Field(
            description="Create a cel on frames in the range that don't already have one"
        ),
    ] = False,
    source_frame_index: Annotated[
        int | None,
        Field(
            description=(
                "When creating a missing cel, the frame index to copy its image from "
                "(defaults to start_frame)"
            )
        ),
    ] = None,
) -> str:
    """Tween cel opacity with easing across a frame range."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if start_opacity < 0 or start_opacity > 255 or end_opacity < 0 or end_opacity > 255:
        return "Opacity must be between 0 and 255"

    easing = (easing or "smoothstep").lower().strip()
    if easing not in {"linear", "ease_in", "ease_out", "ease_in_out", "smoothstep"}:
        return "Unsupported easing (linear, ease_in, ease_out, ease_in_out, smoothstep)"

    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_missing_cels else "false"
    source_idx = "nil" if source_frame_index is None else str(source_frame_index)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target_layer = find_layer(spr, "{safe_layer_name}")
    if not target_layer then print("ERROR:Layer not found") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    local function ease(t)
        local mode = "{easing}"
        if mode == "linear" then return t end
        if mode == "ease_in" then return t * t end
        if mode == "ease_out" then return 1 - (1 - t) * (1 - t) end
        if mode == "ease_in_out" then
            if t < 0.5 then return 2 * t * t end
            local u = -2 * t + 2
            return 1 - (u * u) / 2
        end
        return t * t * (3 - 2 * t)
    end

    local span = end_idx - start_idx
    app.transaction(function()
        for fi = start_idx, end_idx do
            local t = 0
            if span > 0 then
                t = (fi - start_idx) / span
            end
            local e = ease(t)
            local op = math.floor({start_opacity} + ({end_opacity} - {start_opacity}) * e + 0.5)
            if op < 0 then op = 0 end
            if op > 255 then op = 255 end
            local frame = spr.frames[fi]
            local cel = target_layer:cel(frame)
            if not cel and {create_flag} then
                local source_frame = {source_idx}
                if source_frame == nil then
                    source_frame = start_idx
                end
                local source_cel = target_layer:cel(spr.frames[source_frame])
                if source_cel then
                    local img = source_cel.image:clone()
                    cel = spr:newCel(target_layer, frame, img, source_cel.position)
                else
                    local img = Image(spr.width, spr.height, spr.colorMode)
                    cel = spr:newCel(target_layer, frame, img, Point(0, 0))
                end
            end
            if cel then
                cel.opacity = op
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Tweened cel opacity ({easing}) on '{layer_name}' frames {start_frame}-{end_frame} "
            f"in {filename}"
        )
    return f"Failed to tween cel opacity with easing: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def tween_cel_scale_eased(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cels to scale")
    ],
    start_frame: Annotated[
        int, Field(description="Starting frame index of the tween range (1-based)")
    ],
    end_frame: Annotated[
        int,
        Field(description="Ending frame index of the tween range (1-based, inclusive)"),
    ],
    start_scale: Annotated[
        float,
        Field(
            description="Scale multiplier applied to the source cel at start_frame (1.0 = original size)"
        ),
    ],
    end_scale: Annotated[
        float,
        Field(
            description="Scale multiplier applied to the source cel at end_frame (1.0 = original size)"
        ),
    ],
    easing: Annotated[
        str,
        Field(
            description=(
                "Easing curve applied to the tween progress: one of "
                "'linear', 'ease_in', 'ease_out', 'ease_in_out', 'smoothstep'"
            )
        ),
    ] = "smoothstep",
    anchor: Annotated[
        str,
        Field(description="Point the scaling is anchored to: 'center' or 'topleft'"),
    ] = "center",
    replace: Annotated[
        bool,
        Field(
            description="Delete each destination frame's existing cel before writing the scaled one"
        ),
    ] = True,
    create_missing_cels: Annotated[
        bool,
        Field(
            description="Create a cel on frames in the range that don't already have one"
        ),
    ] = True,
    source_frame_index: Annotated[
        int | None,
        Field(
            description=(
                "Frame index to read the source image and position from before scaling "
                "(defaults to start_frame)"
            )
        ),
    ] = None,
) -> str:
    """Tween cel scale with easing across a frame range.

    Reads the source cel's image once, then on every frame in the range
    (by default including the source frame itself) deletes any existing
    cel and writes a resized copy at the eased scale for that frame — so
    with the default replace=True and create_missing_cels=True this
    overwrites every cel in start_frame..end_frame, and re-running it is
    NOT a no-op: each call rescales relative to whatever image is on the
    source frame at call time.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if start_scale <= 0 or end_scale <= 0:
        return "Scale must be > 0"

    easing = (easing or "smoothstep").lower().strip()
    if easing not in {"linear", "ease_in", "ease_out", "ease_in_out", "smoothstep"}:
        return "Unsupported easing (linear, ease_in, ease_out, ease_in_out, smoothstep)"

    anchor = (anchor or "center").lower().strip()
    if anchor not in {"center", "topleft"}:
        return "Unsupported anchor (center, topleft)"

    safe_layer_name = lua_escape(layer_name)
    create_flag = "true" if create_missing_cels else "false"
    replace_flag = "true" if replace else "false"
    source_idx = "nil" if source_frame_index is None else str(source_frame_index)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target_layer = find_layer(spr, "{safe_layer_name}")
    if not target_layer then print("ERROR:Layer not found") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    local source_frame = {source_idx}
    if source_frame == nil then
        source_frame = start_idx
    end
    if source_frame < 1 or source_frame > #spr.frames then
        print("ERROR:Source frame out of range") return
    end

    local source_cel = target_layer:cel(spr.frames[source_frame])
    if not source_cel then
        print("ERROR:Source cel not found") return
    end

    local base_img = source_cel.image:clone()
    local base_w = base_img.width
    local base_h = base_img.height
    local base_pos = source_cel.position

    local function ease(t)
        local mode = "{easing}"
        if mode == "linear" then return t end
        if mode == "ease_in" then return t * t end
        if mode == "ease_out" then return 1 - (1 - t) * (1 - t) end
        if mode == "ease_in_out" then
            if t < 0.5 then return 2 * t * t end
            local u = -2 * t + 2
            return 1 - (u * u) / 2
        end
        return t * t * (3 - 2 * t)
    end

    local span = end_idx - start_idx
    app.transaction(function()
        for fi = start_idx, end_idx do
            local t = 0
            if span > 0 then
                t = (fi - start_idx) / span
            end
            local e = ease(t)
            local scale = {start_scale} + ({end_scale} - {start_scale}) * e
            local new_w = math.max(1, math.floor(base_w * scale + 0.5))
            local new_h = math.max(1, math.floor(base_h * scale + 0.5))

            local dst_frame = spr.frames[fi]
            local dst_cel = target_layer:cel(dst_frame)
            if dst_cel and {replace_flag} then
                spr:deleteCel(dst_cel)
                dst_cel = nil
            end
            if not dst_cel and {create_flag} then
                local img = base_img:clone()
                img:resize(new_w, new_h)
                local pos_x = base_pos.x
                local pos_y = base_pos.y
                if "{anchor}" == "center" then
                    local cx = base_pos.x + base_w / 2
                    local cy = base_pos.y + base_h / 2
                    pos_x = math.floor(cx - new_w / 2 + 0.5)
                    pos_y = math.floor(cy - new_h / 2 + 0.5)
                end
                dst_cel = spr:newCel(target_layer, dst_frame, img, Point(pos_x, pos_y))
            end
        end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Tweened cel scale ({easing}) on '{layer_name}' frames {start_frame}-{end_frame} "
            f"in {filename}"
        )
    return f"Failed to tween cel scale with easing: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def delete_frame(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    frame_index: Annotated[
        int, Field(description="Index of the frame to delete (1-based)")
    ],
) -> str:
    """Delete a frame by index."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end
    if #spr.frames <= 1 then print("ERROR:Cannot delete the only frame") return end

    app.transaction(function()
        spr:deleteFrame(spr.frames[idx])
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Frame {frame_index} deleted from {filename}"
    return f"Failed to delete frame: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def delete_tag(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    name: Annotated[str, Field(description="Name of the tag to delete")],
) -> str:
    """Delete an animation tag by name."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_name = lua_escape(name)
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local target = nil
    for _, tag in ipairs(spr.tags) do
        if tag.name == "{safe_name}" then target = tag break end
    end
    if not target then print("ERROR:Tag not found") return end

    app.transaction(function()
        spr:deleteTag(target)
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Tag '{name}' deleted from {filename}"
    return f"Failed to delete tag: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_cel_opacity(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer containing the cel")
    ],
    frame_index: Annotated[
        int, Field(description="Frame index of the cel to modify (1-based)")
    ],
    opacity: Annotated[
        int,
        Field(
            description="Opacity to set, from 0 (fully transparent) to 255 (fully opaque)"
        ),
    ],
) -> str:
    """Set the opacity of a single cel (0-255)."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not (0 <= opacity <= 255):
        return "Opacity must be between 0 and 255"

    safe_layer = lua_escape(layer_name)
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
        cel.opacity = {opacity}
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Cel opacity set to {opacity} on '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to set cel opacity: {output}"
