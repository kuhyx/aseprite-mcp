import json
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.commands import AsepriteCommand, lua_escape
from ..core.paths import path_exists

_FIND_SLICE = """
local function find_slice(spr, name)
    for _, slice in ipairs(spr.slices) do
        if slice.name == name then return slice end
    end
    return nil
end
"""


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def create_slice(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    name: Annotated[str, Field(description="Slice name")],
    x: Annotated[int, Field(description="Left edge of the slice")],
    y: Annotated[int, Field(description="Top edge of the slice")],
    width: Annotated[int, Field(description="Slice width")],
    height: Annotated[int, Field(description="Slice height")],
) -> str:
    """Create a named slice (a rectangular region usable by game engines).

    Fails if a slice with the same name already exists; each call creates
    a new slice rather than updating one.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"
    if not name:
        return "Slice name cannot be empty"

    safe_name = lua_escape(name)
    script = f"""
    {_FIND_SLICE}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    if find_slice(spr, "{safe_name}") then print("ERROR:Slice with that name already exists") return end

    app.transaction(function()
        local slice = spr:newSlice(Rectangle({x}, {y}, {width}, {height}))
        slice.name = "{safe_name}"
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Slice '{name}' created at ({x},{y}) {width}x{height} in {filename}"
    return f"Failed to create slice: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_slice_center(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    name: Annotated[str, Field(description="Slice name")],
    x: Annotated[
        int, Field(description="Center-rect left edge, relative to the slice")
    ],
    y: Annotated[int, Field(description="Center-rect top edge, relative to the slice")],
    width: Annotated[int, Field(description="Center-rect width")],
    height: Annotated[int, Field(description="Center-rect height")],
) -> str:
    """Set a slice's 9-patch center rectangle (relative to the slice origin).

    The center defines the stretchable region for 9-patch scaling in
    game engines. Calling this again with the same values leaves the
    slice unchanged.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if width <= 0 or height <= 0:
        return "Width and height must be > 0"

    safe_name = lua_escape(name)
    script = f"""
    {_FIND_SLICE}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local slice = find_slice(spr, "{safe_name}")
    if not slice then print("ERROR:Slice not found") return end

    app.transaction(function()
        slice.center = Rectangle({x}, {y}, {width}, {height})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Slice '{name}' 9-patch center set to ({x},{y}) {width}x{height} in {filename}"
    return f"Failed to set slice center: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_slice_pivot(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    name: Annotated[str, Field(description="Slice name")],
    x: Annotated[int, Field(description="Pivot x, relative to the slice")],
    y: Annotated[int, Field(description="Pivot y, relative to the slice")],
) -> str:
    """Set a slice's pivot point (relative to the slice origin).

    The pivot is the anchor game engines use when positioning or
    rotating the slice. Calling this again with the same values leaves
    the slice unchanged.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_name = lua_escape(name)
    script = f"""
    {_FIND_SLICE}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local slice = find_slice(spr, "{safe_name}")
    if not slice then print("ERROR:Slice not found") return end

    app.transaction(function()
        slice.pivot = Point({x}, {y})
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Slice '{name}' pivot set to ({x},{y}) in {filename}"
    return f"Failed to set slice pivot: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def list_slices(
    filename: Annotated[str, Field(description="Aseprite file to inspect")],
) -> str:
    """List all slices with their bounds, 9-patch centers, and pivots.

    Use this to discover existing slice names/bounds before editing or
    referencing them from other tools.

    Returns:
        JSON array of {name, x, y, width, height, center?, pivot?}.

    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    # Emit one JSON object per slice (name via Lua %q) instead of a
    # '|'-delimited line, so a '|' (or comma/colon) in a slice name can no
    # longer break the parse for the whole sprite.
    script = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    for _, slice in ipairs(spr.slices) do
        local b = slice.bounds
        local parts = {}
        parts[#parts + 1] = string.format('"name":%s', string.format("%q", slice.name))
        parts[#parts + 1] = string.format('"x":%d,"y":%d,"width":%d,"height":%d', b.x, b.y, b.width, b.height)
        if slice.center then
            local c = slice.center
            parts[#parts + 1] = string.format('"center":{"x":%d,"y":%d,"width":%d,"height":%d}', c.x, c.y, c.width, c.height)
        end
        if slice.pivot then
            parts[#parts + 1] = string.format('"pivot":{"x":%d,"y":%d}', slice.pivot.x, slice.pivot.y)
        end
        print("SLICE:{" .. table.concat(parts, ",") .. "}")
    end
    print("DONE")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to list slices: {output}"

    slices = []
    for line in output.splitlines():
        if not line.startswith("SLICE:"):
            continue
        slices.append(json.loads(line[len("SLICE:") :]))
    return json.dumps(slices)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def delete_slice(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    name: Annotated[str, Field(description="Slice name to delete")],
) -> str:
    """Delete a slice by name.

    Deleting a slice that does not exist leaves the sprite unchanged
    (reported as an error), so repeated calls are idempotent.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_name = lua_escape(name)
    script = f"""
    {_FIND_SLICE}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local slice = find_slice(spr, "{safe_name}")
    if not slice then print("ERROR:Slice not found") return end

    app.transaction(function()
        spr:deleteSlice(slice)
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Slice '{name}' deleted from {filename}"
    return f"Failed to delete slice: {output}"
