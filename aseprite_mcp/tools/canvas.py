from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from ..core.lua import FIND_LAYER
from ..core.paths import path_exists


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def create_canvas(
    width: Annotated[int, Field(description="Width of the canvas in pixels")],
    height: Annotated[int, Field(description="Height of the canvas in pixels")],
    filename: Annotated[
        str, Field(description="Name of the output .aseprite file to create")
    ] = "canvas.aseprite",
) -> str:
    """Create a new Aseprite canvas with specified dimensions.

    WARNING: writes unconditionally — if filename already exists, it is
    silently overwritten with a blank canvas with no confirmation prompt.
    """
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"
    err = reject_traversal(filename)
    if err:
        return err

    safe_path = lua_escape(filename.replace("\\", "/"))
    script = f"""
    local spr = Sprite({width}, {height})
    spr:saveAs("{safe_path}")
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script)
    if not success:
        return f"Failed to create canvas: {output}"

    # Sprite:saveAs() fails silently when the destination cannot be written
    # (e.g. a directory with no write permission): it raises nothing, so the
    # script still reaches print("OK"). The file's existence is the only
    # trustworthy signal that the canvas was actually created.
    if not await path_exists(filename):
        return (
            f"Failed to create canvas: Aseprite reported success but "
            f"{filename} was not created (is the destination writable?)"
        )
    return f"Canvas created successfully: {filename}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def add_layer(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Name of the new layer")],
    group: Annotated[
        str,
        Field(
            description="Optional group to place the new layer inside, by name "
            "or 'group/subgroup' path (default: top level)"
        ),
    ] = "",
) -> str:
    """Add a new layer to the Aseprite file.

    Each call creates another new layer, even if a layer with the same name
    already exists — call this once per layer you want to add.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer_name = lua_escape(layer_name)
    safe_group = lua_escape(group)
    script = f"""
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local parent = nil
    if "{safe_group}" ~= "" then
        parent = find_layer(spr, "{safe_group}")
        if not parent then print("ERROR:Group not found") return end
        if not parent.isGroup then print("ERROR:Target is not a group") return end
    end

    app.transaction(function()
        local lyr = spr:newLayer()
        lyr.name = "{safe_layer_name}"
        if parent then lyr.parent = parent end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        location = f" inside group '{group}'" if group else ""
        return f"Layer '{layer_name}' added{location} to {filename}"
    return f"Failed to add layer: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def add_group(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    group_name: Annotated[str, Field(description="Name of the new group")],
    parent_group: Annotated[
        str,
        Field(
            description="Optional existing group to nest the new group inside, "
            "by name or 'group/subgroup' path (default: top level)"
        ),
    ] = "",
) -> str:
    """Add a new, empty group layer.

    Combine with add_layer(group=...) / duplicate_layer(group=...) to build a
    grouped layer structure. Each call creates another new group, even if one
    with the same name already exists.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_group = lua_escape(group_name)
    safe_parent = lua_escape(parent_group)
    script = f"""
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local parent = nil
    if "{safe_parent}" ~= "" then
        parent = find_layer(spr, "{safe_parent}")
        if not parent then print("ERROR:Parent group not found") return end
        if not parent.isGroup then print("ERROR:Target is not a group") return end
    end

    app.transaction(function()
        local grp = spr:newGroup()
        grp.name = "{safe_group}"
        if parent then grp.parent = parent end
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        location = f" inside '{parent_group}'" if parent_group else ""
        return f"Group '{group_name}' created{location} in {filename}"
    return f"Failed to create group: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def add_frame(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
) -> str:
    """Add a new frame to the Aseprite file.

    Each call appends another new frame — calling it twice adds two frames,
    not one.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    script = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.transaction(function()
        spr:newFrame()
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"New frame added successfully to {filename}"
    return f"Failed to add frame: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_frame(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    frame_index: Annotated[
        int, Field(description="Frame index to activate, starting at 1")
    ],
) -> str:
    """Set the active frame by index (1-based)."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then
        print("ERROR:Frame index out of range") return
    end

    app.transaction(function()
        app.activeFrame = spr.frames[idx]
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"Active frame set to {frame_index} in {filename}"
    return f"Failed to set frame: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_frame_duration(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    frame_index: Annotated[
        int, Field(description="Frame index to update, starting at 1")
    ],
    duration_ms: Annotated[
        int, Field(description="New frame duration in milliseconds")
    ],
) -> str:
    """Set the duration of a frame in milliseconds."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if duration_ms <= 0:
        return "Duration must be > 0"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then
        print("ERROR:Frame index out of range") return
    end

    app.transaction(function()
        spr.frames[idx].duration = {duration_ms} / 1000.0
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"Frame {frame_index} duration set to {duration_ms}ms in {filename}"
    return f"Failed to set frame duration: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_layer(
    filename: Annotated[str, Field(description="Name of the Aseprite file to modify")],
    layer_name: Annotated[str, Field(description="Layer name to activate")],
    create_if_missing: Annotated[
        bool, Field(description="Create the layer if it does not already exist")
    ] = False,
) -> str:
    """Set the active layer by name.

    Looks up an existing layer by name and re-uses it if create_if_missing is
    set, so calling this again with the same name does not create a second
    layer.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    create_flag = "true" if create_if_missing else "false"
    safe_layer_name = lua_escape(layer_name)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target and not {create_flag} then print("ERROR:Layer not found") return end

    app.transaction(function()
        if not target then
            target = spr:newLayer()
            target.name = "{safe_layer_name}"
        end
        app.activeLayer = target
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)

    if success:
        return f"Active layer set to '{layer_name}' in {filename}"
    return f"Failed to set layer: {output}"
