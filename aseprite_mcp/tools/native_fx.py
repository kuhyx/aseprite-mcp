"""Native Aseprite filter/command wrappers (app.command.*).

These delegate to Aseprite's own engine filters instead of hand-rolling
pixel math in Lua — higher quality and faster than the equivalents in
fx.py. All verified to run headless under --batch (T0, 2026-06-18). They
are added ALONGSIDE the hand-rolled tools (outline_cel / adjust_hsl /
quantize_to_palette stay) per the "deprecate, don't break" policy.

General value (upstream-able): nothing Chimera-specific here.
"""

import json
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.commands import AsepriteCommand, lua_escape
from ..core.native import build_native_command_script
from ..core.paths import path_exists
from .fx import _parse_hex_color

_HUE_MAX = 180
_PERCENT_SHIFT_MAX = 100
_PALETTE_SIZE_MAX = 256

# Built-in convolution-matrix resource names (Aseprite data/convmatr.def).
CONVOLUTION_MATRICES = frozenset(
    {
        "brightness",
        "contrast",
        "negative",
        "blur-3x3",
        "blur-3x3-hard",
        "blur-5x5",
        "blur-7x7",
        "blur-9x9",
        "blur-17x17",
        "blur-5x3-left",
        "blur-17x3-left",
        "blur-3x17-top",
        "blur-5x5-diagonal(\\)",
        "blur-5x5-diagonal(/)",
        "sharpen-3x3",
        "sharpen-5x5",
        "sharpen-7x7",
        "edges-find",
        "edges-find-horizontal",
        "edges-find-vertical",
        "misc-contour",
        "misc-texturize",
        "misc-emboss",
        "misc-marmolize",
        "misc-rock",
        "misc-rock-edges",
        "drunk-3x3_x",
        "drunk-3x3_+",
        "drunk-5x5_x",
        "drunk-5x5_+",
        "drunk-7x7_x",
        "drunk-7x7_+",
        "drunk-9x9_x",
        "drunk-9x9_+",
        "drunk-17x17_x",
        "drunk-17x17_+",
        "drunk-17x17_o",
        "outline-transparent-layer-(cross)",
        "outline-transparent-layer-(square)",
    }
)


def _region(
    x: int, y: int, width: int, height: int
) -> tuple[int, int, int, int] | None:
    return (x, y, width, height) if width > 0 and height > 0 else None


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def outline_native(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Layer to outline (empty = active layer)")
    ] = "",
    frame_index: Annotated[int, Field(description="1-based frame index")] = 1,
    color: Annotated[str, Field(description="Outline colour as #RRGGBB")] = "#000000",
    place: Annotated[
        str, Field(description="Outline placement: 'outside' or 'inside'")
    ] = "outside",
    matrix: Annotated[
        str, Field(description="Outline brush shape: 'circle' or 'square'")
    ] = "circle",
) -> str:
    """Native Aseprite Outline around opaque pixels (app.command.Outline).

    Higher quality than the 1px hand-rolled outline_cel: inside/outside
    placement + a circle/square brush. Works best on a full-canvas cel.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    rgb = _parse_hex_color(color)
    if not rgb:
        return "Invalid color (expected #RRGGBB)"
    if place not in ("outside", "inside"):
        return "place must be 'outside' or 'inside'"
    if matrix not in ("circle", "square"):
        return "matrix must be 'circle' or 'square'"
    r, g, b = rgb
    cmd = (
        f"        app.command.Outline{{ui=false, color=Color{{r={r}, g={g}, "
        f'b={b}, a=255}}, place="{place}", matrix="{matrix}"}}'
    )
    script = build_native_command_script(cmd, layer_name, frame_index)
    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return (
            f"Outlined ({place}, {matrix}) {layer_name or 'active layer'} in {filename}"
        )
    return f"Failed to outline: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def adjust_hsl_native(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Layer to adjust (empty = active layer)")
    ] = "",
    frame_index: Annotated[int, Field(description="1-based frame index")] = 1,
    hue: Annotated[int, Field(description="Hue shift in degrees, -180..180")] = 0,
    saturation: Annotated[int, Field(description="Saturation shift, -100..100")] = 0,
    lightness: Annotated[int, Field(description="Lightness shift, -100..100")] = 0,
    x: Annotated[
        int,
        Field(
            description="Region left edge; 0 with width/height unset scopes the whole layer"
        ),
    ] = 0,
    y: Annotated[
        int,
        Field(
            description="Region top edge; 0 with width/height unset scopes the whole layer"
        ),
    ] = 0,
    width: Annotated[
        int,
        Field(
            description="Region width in pixels; >0 together with height>0 scopes the filter to a rectangle"
        ),
    ] = 0,
    height: Annotated[
        int,
        Field(
            description="Region height in pixels; >0 together with width>0 scopes the filter to a rectangle"
        ),
    ] = 0,
) -> str:
    """Native Hue/Saturation/Lightness filter (engine-quality vs adjust_hsl).

    Shifts hue/saturation/lightness on a layer or cel region using
    Aseprite's own engine filter for higher quality than the hand-rolled
    adjust_hsl.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not (-_HUE_MAX <= hue <= _HUE_MAX):
        return f"hue must be -{_HUE_MAX}..{_HUE_MAX}"
    if not (-_PERCENT_SHIFT_MAX <= saturation <= _PERCENT_SHIFT_MAX) or not (
        -_PERCENT_SHIFT_MAX <= lightness <= _PERCENT_SHIFT_MAX
    ):
        return (
            f"saturation and lightness must be "
            f"-{_PERCENT_SHIFT_MAX}..{_PERCENT_SHIFT_MAX}"
        )
    cmd = (
        f"        app.command.HueSaturation{{ui=false, hue={hue}, "
        f"saturation={saturation}, lightness={lightness}, alpha=0}}"
    )
    script = build_native_command_script(
        cmd, layer_name, frame_index, _region(x, y, width, height)
    )
    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Adjusted HSL on {layer_name or 'active layer'} in {filename}"
    return f"Failed to adjust HSL: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def adjust_brightness_contrast(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Layer to adjust (empty = active layer)")
    ] = "",
    frame_index: Annotated[int, Field(description="1-based frame index")] = 1,
    brightness: Annotated[int, Field(description="Brightness shift, -100..100")] = 0,
    contrast: Annotated[int, Field(description="Contrast shift, -100..100")] = 0,
    x: Annotated[
        int,
        Field(
            description="Region left edge; 0 with width/height unset scopes the whole layer"
        ),
    ] = 0,
    y: Annotated[
        int,
        Field(
            description="Region top edge; 0 with width/height unset scopes the whole layer"
        ),
    ] = 0,
    width: Annotated[
        int,
        Field(
            description="Region width in pixels; >0 together with height>0 scopes the filter to a rectangle"
        ),
    ] = 0,
    height: Annotated[
        int,
        Field(
            description="Region height in pixels; >0 together with width>0 scopes the filter to a rectangle"
        ),
    ] = 0,
) -> str:
    """Native Brightness/Contrast filter (app.command.BrightnessContrast).

    Applies Aseprite's own brightness/contrast engine filter to a layer or
    cel region.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not (-_PERCENT_SHIFT_MAX <= brightness <= _PERCENT_SHIFT_MAX) or not (
        -_PERCENT_SHIFT_MAX <= contrast <= _PERCENT_SHIFT_MAX
    ):
        return (
            f"brightness and contrast must be "
            f"-{_PERCENT_SHIFT_MAX}..{_PERCENT_SHIFT_MAX}"
        )
    cmd = (
        f"        app.command.BrightnessContrast{{ui=false, "
        f"brightness={brightness}, contrast={contrast}}}"
    )
    script = build_native_command_script(
        cmd, layer_name, frame_index, _region(x, y, width, height)
    )
    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Adjusted brightness/contrast on {layer_name or 'active layer'} in {filename}"
    return f"Failed to adjust brightness/contrast: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def invert_colors(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Layer to invert (empty = active layer)")
    ] = "",
    frame_index: Annotated[int, Field(description="1-based frame index")] = 1,
    x: Annotated[
        int,
        Field(
            description="Region left edge; 0 with width/height unset scopes the whole layer"
        ),
    ] = 0,
    y: Annotated[
        int,
        Field(
            description="Region top edge; 0 with width/height unset scopes the whole layer"
        ),
    ] = 0,
    width: Annotated[
        int,
        Field(
            description="Region width in pixels; >0 together with height>0 scopes the filter to a rectangle"
        ),
    ] = 0,
    height: Annotated[
        int,
        Field(
            description="Region height in pixels; >0 together with width>0 scopes the filter to a rectangle"
        ),
    ] = 0,
) -> str:
    """Native colour inversion (app.command.InvertColor).

    Inverts RGB colour values on a layer or cel region. Calling it twice on
    the same region restores the original colours instead of leaving it
    inverted, so treat it as a toggle rather than a "set inverted" call.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    cmd = "        app.command.InvertColor{ui=false}"
    script = build_native_command_script(
        cmd, layer_name, frame_index, _region(x, y, width, height)
    )
    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Inverted colours on {layer_name or 'active layer'} in {filename}"
    return f"Failed to invert: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def apply_convolution(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    matrix: Annotated[
        str,
        Field(
            description="Built-in matrix name (see list_convolution_matrices), "
            "e.g. 'blur-3x3', 'sharpen-3x3', 'edges-find', 'misc-emboss'"
        ),
    ],
    layer_name: Annotated[
        str, Field(description="Layer to filter (empty = active layer)")
    ] = "",
    frame_index: Annotated[int, Field(description="1-based frame index")] = 1,
    x: Annotated[
        int,
        Field(
            description="Region left edge; 0 with width/height unset scopes the whole layer"
        ),
    ] = 0,
    y: Annotated[
        int,
        Field(
            description="Region top edge; 0 with width/height unset scopes the whole layer"
        ),
    ] = 0,
    width: Annotated[
        int,
        Field(
            description="Region width in pixels; >0 together with height>0 scopes the filter to a rectangle"
        ),
    ] = 0,
    height: Annotated[
        int,
        Field(
            description="Region height in pixels; >0 together with width>0 scopes the filter to a rectangle"
        ),
    ] = 0,
) -> str:
    """Native convolution filter (blur / sharpen / edge / emboss …).

    Applies a built-in Aseprite convolution matrix (blur, sharpen, edge
    detection, emboss, and more) to a layer or cel region.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if matrix not in CONVOLUTION_MATRICES:
        return (
            f"Unknown matrix {matrix!r}; call list_convolution_matrices for "
            f"the {len(CONVOLUTION_MATRICES)} valid names"
        )
    cmd = f'        app.command.ConvolutionMatrix{{ui=false, fromResource="{lua_escape(matrix)}"}}'
    script = build_native_command_script(
        cmd, layer_name, frame_index, _region(x, y, width, height)
    )
    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Applied convolution '{matrix}' on {layer_name or 'active layer'} in {filename}"
    return f"Failed to apply convolution: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def list_convolution_matrices() -> str:
    """List the built-in convolution-matrix names usable with apply_convolution.

    Returns:
        JSON array of matrix resource names.
    """
    return json.dumps(sorted(CONVOLUTION_MATRICES))


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def extract_palette(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    max_colors: Annotated[
        int,
        Field(description="Palette size cap, 1..256 (fewer if the art has fewer)"),
    ] = 16,
    with_alpha: Annotated[
        bool, Field(description="Include alpha channel when quantizing")
    ] = False,
) -> str:
    """Build an OPTIMAL palette from the sprite via native ColorQuantization.

    True palette extraction (vs the nearest-snap quantize_to_palette): writes
    the resulting palette to the sprite and returns it. NOTE: mutates the
    sprite's palette. Sprite must be in RGB mode.

    Returns:
        JSON {colors: [#RRGGBB, ...], count}
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not (1 <= max_colors <= _PALETTE_SIZE_MAX):
        return f"max_colors must be 1..{_PALETTE_SIZE_MAX}"
    wa = "true" if with_alpha else "false"
    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end
    app.transaction(function()
        app.command.ColorQuantization{{ui=false, maxColors={max_colors}, withAlpha={wa}}}
    end)
    spr:saveAs(spr.filename)
    local pal = spr.palettes[1]
    for i = 0, #pal - 1 do
        local c = pal:getColor(i)
        print(string.format("PALETTE:#%02X%02X%02X", c.red, c.green, c.blue))
    end
    print("OK")
    """
    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if not success:
        return f"Failed to extract palette: {output}"
    colors = [
        ln[len("PALETTE:") :] for ln in output.splitlines() if ln.startswith("PALETTE:")
    ]
    return json.dumps({"colors": colors, "count": len(colors)})
