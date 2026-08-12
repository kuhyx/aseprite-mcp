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
async def copy_layers_between_sprites(
    source_filename: Annotated[
        str, Field(description="Source .aseprite file to copy layers from")
    ],
    target_filename: Annotated[
        str, Field(description="Target .aseprite file to copy layers into")
    ],
    layer_names: Annotated[list[str], Field(description="Names of the layers to copy")],
    replace: Annotated[
        bool, Field(description="Overwrite existing cels on matching target layers")
    ] = True,
    create_missing_frames: Annotated[
        bool,
        Field(
            description="Add frames to the target sprite if it has fewer than the source"
        ),
    ] = True,
) -> str:
    """Copy layers by name from a source sprite to a target sprite."""
    if not await path_exists(source_filename):
        return f"File {source_filename} not found"
    if not await path_exists(target_filename):
        return f"File {target_filename} not found"
    if not layer_names:
        return "Layer names list cannot be empty"
    err = reject_traversal(source_filename) or reject_traversal(target_filename)
    if err:
        return err

    src_path = lua_escape(source_filename.replace("\\", "/"))
    dst_path = lua_escape(target_filename.replace("\\", "/"))
    replace_flag = "true" if replace else "false"
    create_frames_flag = "true" if create_missing_frames else "false"
    layers_lua = "{" + ",".join([f'"{lua_escape(name)}"' for name in layer_names]) + "}"

    script = f"""
    local src = app.open("{src_path}")
    if not src then print("ERROR:Source sprite not opened") return end
    local dst = app.open("{dst_path}")
    if not dst then print("ERROR:Target sprite not opened") return end

    {FIND_LAYER}

    local names = {layers_lua}
    local missing = {{}}
    local valid = {{}}
    for _, name in ipairs(names) do
        if find_layer(src, name) then
            table.insert(valid, name)
        else
            table.insert(missing, name)
        end
    end
    if #valid == 0 then
        print("ERROR:None of the requested layers exist in the source: " .. table.concat(missing, ", ")) return
    end

    app.transaction(function()
        if {create_frames_flag} then
            while #dst.frames < #src.frames do
                dst:newFrame()
            end
        end

        for _, name in ipairs(valid) do
            local src_layer = find_layer(src, name)
            local dst_layer = find_layer(dst, name)
            if not dst_layer then
                dst_layer = dst:newLayer()
                dst_layer.name = name
            end
            if {replace_flag} then
                for i = 1, #dst.frames do
                    local cel = dst_layer:cel(dst.frames[i])
                    if cel then dst:deleteCel(cel) end
                end
            end
            for i = 1, #src.frames do
                if i <= #dst.frames then
                    local src_cel = src_layer:cel(src.frames[i])
                    if src_cel then
                        local dst_cel = dst_layer:cel(dst.frames[i])
                        if dst_cel and {replace_flag} then
                            dst:deleteCel(dst_cel)
                            dst_cel = nil
                        end
                        if not dst_cel then
                            local img = src_cel.image:clone()
                            dst:newCel(dst_layer, dst.frames[i], img, src_cel.position)
                        end
                    end
                end
            end
        end
    end)

    dst:saveAs(dst.filename)
    if #missing > 0 then
        print("MISSING:" .. table.concat(missing, ", "))
    end
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script)
    if not success:
        return f"Failed to copy layers: {output}"
    missing = next(
        (
            line[len("MISSING:") :]
            for line in output.splitlines()
            if line.startswith("MISSING:")
        ),
        None,
    )
    msg = f"Layers copied from {source_filename} to {target_filename}"
    if missing:
        msg += f" (skipped missing layers: {missing})"
    return msg
