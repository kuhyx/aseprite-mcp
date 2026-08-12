import glob
import os
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.commands import AsepriteCommand, lua_escape, reject_traversal
from ..core.lua import FIND_LAYER, NORMALIZE_CEL
from ..core.paths import path_exists

_EXPORT_SCALE_MAX = 64


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def export_sprite(
    filename: Annotated[str, Field(description="Name of the Aseprite file to export")],
    output_filename: Annotated[str, Field(description="Name of the output file")],
    output_format: Annotated[
        str,
        Field(
            description='Output format, e.g. "png", "gif", "jpg" (default "png")',
        ),
    ] = "png",
) -> str:
    """Export the Aseprite file to another format."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    # Make sure output_format is lowercase
    output_format = output_format.lower()

    # Ensure output filename has the correct extension
    if not output_filename.lower().endswith(f".{output_format}"):
        output_filename = f"{output_filename}.{output_format}"

    # For animated exports
    if output_format == "gif":
        args = ["--batch", filename, "--save-as", output_filename]
        success, output = AsepriteCommand.run_command(args)
    else:
        # For still image exports
        args = ["--batch", filename, "--save-as", output_filename]
        success, output = AsepriteCommand.run_command(args)

    # Aseprite exits 0 even when it cannot write the requested format
    # (e.g. output_format="json"). Confirm a file actually appeared. A multi-frame
    # sprite saved to a still format produces frame-numbered siblings
    # (out1.png, out2.png, ...) instead of the exact name, so accept those
    # too — same convention as export_frame.
    if success:
        base, ext = os.path.splitext(output_filename)
        if not await path_exists(output_filename) and not glob.glob(f"{base}*{ext}"):
            success = False
            output = "Aseprite exited 0 but wrote no file (the format may not be writable via --save-as)"

    if success:
        return f"Sprite exported successfully to {output_filename}"
    return f"Failed to export sprite: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def copy_sprite(
    filename: Annotated[str, Field(description="Name of the Aseprite file to copy")],
    output_filename: Annotated[
        str, Field(description="Name of the output .aseprite file")
    ],
    overwrite: Annotated[
        bool, Field(description="Whether to overwrite if output exists")
    ] = False,
) -> str:
    """Copy a sprite to a new Aseprite file.

    The source file is only read; nothing about it is modified. When
    overwrite is True and output_filename already exists, that existing
    file is replaced.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    if not output_filename.lower().endswith(".aseprite"):
        output_filename = f"{output_filename}.aseprite"

    err = reject_traversal(output_filename)
    if err:
        return err

    if await path_exists(output_filename) and not overwrite:
        return f"Output file {output_filename} already exists"

    safe_path = lua_escape(output_filename.replace("\\", "/"))
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    spr:saveAs("{safe_path}")
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success and not await path_exists(output_filename):
        success = False
        output = "Aseprite exited 0 but wrote no file"
    if success:
        return f"Sprite copied to {output_filename}"
    return f"Failed to copy sprite: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def export_frame(
    filename: Annotated[str, Field(description="Aseprite file to export")],
    frame_index: Annotated[int, Field(description="Frame index starting at 1")],
    output_filename: Annotated[str, Field(description="Output PNG path")],
    scale: Annotated[
        int, Field(description="Integer nearest-neighbor scale factor (default 1)")
    ] = 1,
) -> str:
    """Export a single frame as a PNG, optionally scaled up.

    Use this for visual feedback while drawing: export at scale 8-10 and
    open the PNG to inspect the result, then keep iterating.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if scale < 1 or scale > _EXPORT_SCALE_MAX:
        return f"scale must be between 1 and {_EXPORT_SCALE_MAX}"
    err = reject_traversal(output_filename)
    if err:
        return err
    if not output_filename.lower().endswith(".png"):
        output_filename = f"{output_filename}.png"

    f0 = frame_index - 1  # CLI --frame-range is 0-based
    args = [
        "--batch",
        filename,
        "--frame-range",
        f"{f0},{f0}",
        "--scale",
        str(scale),
        "--save-as",
        output_filename,
    ]
    success, output = AsepriteCommand.run_command(args)
    if not success:
        return f"Failed to export frame: {output}"

    # With multi-frame sprites Aseprite may append the frame number to
    # the filename; rename the produced file when that happens.
    if not await path_exists(output_filename):
        base, ext = os.path.splitext(output_filename)
        candidates = sorted(glob.glob(f"{base}*{ext}"))
        if candidates:
            os.replace(candidates[0], output_filename)
        else:
            return f"Export reported success but {output_filename} was not created"
    return f"Frame {frame_index} exported to {output_filename} at {scale}x"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def export_spritesheet(
    filename: Annotated[str, Field(description="Aseprite file to export")],
    output_filename: Annotated[str, Field(description="Output sheet image path (PNG)")],
    sheet_type: Annotated[
        str,
        Field(
            description=(
                'Layout: "horizontal", "vertical", "rows", "columns", or "packed"'
            ),
        ),
    ] = "horizontal",
    data_filename: Annotated[
        str, Field(description="Optional path for a JSON metadata file")
    ] = "",
    scale: Annotated[
        int,
        Field(description="Integer scale factor applied before packing (default 1)"),
    ] = 1,
    padding: Annotated[
        int, Field(description="Padding in pixels between frames (default 0)")
    ] = 0,
    tag_name: Annotated[
        str,
        Field(
            description="Only include frames of this animation tag (default: all frames)"
        ),
    ] = "",
    data_format: Annotated[
        str,
        Field(
            description='JSON format for the data file: "json-array" (default) or "json-hash"'
        ),
    ] = "json-array",
    list_tags: Annotated[
        bool,
        Field(
            description="Include animation tag metadata in the JSON data file (default False)"
        ),
    ] = False,
) -> str:
    """Export frames as a sprite sheet, optionally with a JSON data file."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if sheet_type not in ("horizontal", "vertical", "rows", "columns", "packed"):
        return "sheet_type must be one of: horizontal, vertical, rows, columns, packed"
    if scale < 1 or scale > _EXPORT_SCALE_MAX:
        return f"scale must be between 1 and {_EXPORT_SCALE_MAX}"
    if padding < 0:
        return "padding must be >= 0"
    if data_format not in ("json-array", "json-hash"):
        return "data_format must be 'json-array' or 'json-hash'"
    err = reject_traversal(output_filename)
    if err:
        return err
    if not output_filename.lower().endswith(".png"):
        output_filename = f"{output_filename}.png"

    args = ["--batch"]
    if tag_name:
        # Frame filters only apply to --sheet when they appear before
        # the input file; resolve the tag to a 0-based --frame-range so
        # missing tags produce a clear error.
        safe_tag = lua_escape(tag_name)
        script = f"""
        local spr = app.activeSprite
        if not spr then print("ERROR:No active sprite") return end
        for _, tag in ipairs(spr.tags) do
            if tag.name == "{safe_tag}" then
                print("RANGE:" .. (tag.fromFrame.frameNumber - 1) .. "," .. (tag.toFrame.frameNumber - 1))
                return
            end
        end
        print("ERROR:Tag not found")
        """
        ok, out = AsepriteCommand.execute_lua_script_checked(script, filename)
        if not ok:
            return f"Failed to resolve tag: {out}"
        frame_range = next(
            (
                line[len("RANGE:") :]
                for line in out.splitlines()
                if line.startswith("RANGE:")
            ),
            None,
        )
        if frame_range is None:
            return "Failed to resolve tag: no range returned"
        args += ["--frame-range", frame_range]
    args.append(filename)
    if scale > 1:
        args += ["--scale", str(scale)]
    args += ["--sheet-type", sheet_type]
    if padding > 0:
        args += ["--shape-padding", str(padding)]
    if data_filename:
        err = reject_traversal(data_filename)
        if err:
            return err
        args += ["--data", data_filename, "--format", data_format]
        if list_tags:
            args.append("--list-tags")
    args += ["--sheet", output_filename]

    success, output = AsepriteCommand.run_command(args)
    if success and not await path_exists(output_filename):
        success = False
        output = "Aseprite exited 0 but wrote no sheet file"
    if success and data_filename and not await path_exists(data_filename):
        success = False
        output = "Aseprite exited 0 but wrote no data file"
    if success:
        msg = f"Sprite sheet exported to {output_filename} ({sheet_type})"
        if data_filename:
            msg += f" with data file {data_filename}"
        return msg
    return f"Failed to export sprite sheet: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def export_layers(
    filename: Annotated[str, Field(description="Aseprite file to export")],
    output_directory: Annotated[
        str, Field(description="Directory for the per-layer PNGs (created if missing)")
    ],
    include_hidden: Annotated[
        bool, Field(description="Also export hidden layers (default False)")
    ] = False,
) -> str:
    """Export each layer as its own PNG file named <layer>.png."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    err = reject_traversal(output_directory)
    if err:
        return err
    os.makedirs(output_directory, exist_ok=True)

    args = ["--batch"]
    if include_hidden:
        args.append("--all-layers")
    args += [
        "--split-layers",
        filename,
        "--save-as",
        os.path.join(output_directory, "{layer}.png"),
    ]
    success, output = AsepriteCommand.run_command(args)
    if not success:
        return f"Failed to export layers: {output}"
    produced = sorted(
        os.path.basename(p) for p in glob.glob(os.path.join(output_directory, "*.png"))
    )
    if not produced:
        return "Failed to export layers: Aseprite exited 0 but wrote no PNG files"
    return f"Layers exported to {output_directory}: {', '.join(produced)}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def export_tag(
    filename: Annotated[str, Field(description="Aseprite file to export")],
    tag_name: Annotated[str, Field(description="Animation tag to export")],
    output_filename: Annotated[
        str,
        Field(description="Output path; .gif gives an animation, .png a sequence"),
    ],
    scale: Annotated[int, Field(description="Integer scale factor (default 1)")] = 1,
) -> str:
    """Export the frames of an animation tag as a GIF or PNG sequence."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if scale < 1 or scale > _EXPORT_SCALE_MAX:
        return f"scale must be between 1 and {_EXPORT_SCALE_MAX}"
    err = reject_traversal(output_filename)
    if err:
        return err

    # --tag silently exports *all* frames (exit 0) when the tag does not
    # exist, so a produced file is not proof the tag was honoured. Validate
    # the tag up front — same approach as export_spritesheet.
    safe_tag = lua_escape(tag_name)
    check = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end
    for _, tag in ipairs(spr.tags) do
        if tag.name == "{safe_tag}" then print("OK") return end
    end
    print("ERROR:Tag not found")
    """
    ok, out = AsepriteCommand.execute_lua_script_checked(check, filename)
    if not ok:
        return f"Failed to export tag: {out}"

    args = ["--batch", filename, "--tag", tag_name]
    if scale > 1:
        args += ["--scale", str(scale)]
    args += ["--save-as", output_filename]
    success, output = AsepriteCommand.run_command(args)
    if success:
        # A multi-frame tag saved to a still format produces frame-numbered
        # siblings instead of the exact name — accept those, same convention
        # as export_sprite/export_frame.
        base, ext = os.path.splitext(output_filename)
        if not await path_exists(output_filename) and not glob.glob(f"{base}*{ext}"):
            success = False
            output = "Aseprite exited 0 but wrote no file"
    if success:
        return f"Tag '{tag_name}' exported to {output_filename}"
    return f"Failed to export tag: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def import_image_as_layer(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    image_path: Annotated[str, Field(description="Image file to import")],
    layer_name: Annotated[str, Field(description="Layer to place the image on")],
    frame_index: Annotated[
        int, Field(description="Frame index starting at 1 (default 1)")
    ] = 1,
    x: Annotated[
        int, Field(description="X position for the image's top-left corner (default 0)")
    ] = 0,
    y: Annotated[
        int, Field(description="Y position for the image's top-left corner (default 0)")
    ] = 0,
) -> str:
    """Import an image file (PNG, etc.) into a layer of the sprite.

    Useful for bringing in reference images or composing pre-made parts.
    The layer is created if it does not exist. Works best when the sprite
    is in RGB color mode. This mutates and saves the source .aseprite file.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not await path_exists(image_path):
        return f"Image {image_path} not found"

    safe_layer = lua_escape(layer_name)
    safe_image = lua_escape(os.path.abspath(image_path).replace("\\", "/"))
    script = f"""
    {FIND_LAYER}
    {NORMALIZE_CEL}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local idx = {frame_index}
    if idx < 1 or idx > #spr.frames then print("ERROR:Frame index out of range") return end

    local src = Image{{ fromFile = "{safe_image}" }}
    if not src then print("ERROR:Could not load image") return end

    local target = find_layer(spr, "{safe_layer}")
    app.transaction(function()
        if not target then
            target = spr:newLayer()
            target.name = "{safe_layer}"
        end
        local cel = normalize_cel(spr, target, spr.frames[idx], true)
        cel.image:drawImage(src, Point({x}, {y}))
    end)

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Image {image_path} imported onto '{layer_name}' frame {frame_index} in {filename}"
    return f"Failed to import image: {output}"
