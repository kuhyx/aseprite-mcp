import colorsys
import json
from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import mcp
from ..core.colors import parse_hex_color
from ..core.commands import AsepriteCommand, lua_escape
from ..core.lua import FIND_LAYER
from ..core.paths import path_exists

_RAMP_STEPS_MIN = 2
_RAMP_STEPS_MAX = 16

# Well-known retro/pixel-art palettes.
PALETTE_PRESETS = {
    "gameboy": ["#0F380F", "#306230", "#8BAC0F", "#9BBC0F"],
    "monochrome": ["#000000", "#FFFFFF"],
    "grayscale_4": ["#000000", "#555555", "#AAAAAA", "#FFFFFF"],
    "cga": ["#000000", "#55FFFF", "#FF55FF", "#FFFFFF"],
    "pico8": [
        "#000000",
        "#1D2B53",
        "#7E2553",
        "#008751",
        "#AB5236",
        "#5F574F",
        "#C2C3C7",
        "#FFF1E8",
        "#FF004D",
        "#FFA300",
        "#FFEC27",
        "#00E436",
        "#29ADFF",
        "#83769C",
        "#FF77A8",
        "#FFCCAA",
    ],
    "c64": [
        "#000000",
        "#FFFFFF",
        "#880000",
        "#AAFFEE",
        "#CC44CC",
        "#00CC55",
        "#0000AA",
        "#EEEE77",
        "#DD8855",
        "#664400",
        "#FF7777",
        "#333333",
        "#777777",
        "#AAFF66",
        "#0088FF",
        "#BBBBBB",
    ],
    "dawnbringer16": [
        "#140C1C",
        "#442434",
        "#30346D",
        "#4E4A4E",
        "#854C30",
        "#346524",
        "#D04648",
        "#757161",
        "#597DCE",
        "#D27D2C",
        "#8595A1",
        "#6DAA2C",
        "#D2AA99",
        "#6DC2CA",
        "#DAD45E",
        "#DEEED6",
    ],
    "dawnbringer32": [
        "#000000",
        "#222034",
        "#45283C",
        "#663931",
        "#8F563B",
        "#DF7126",
        "#D9A066",
        "#EEC39A",
        "#FBF236",
        "#99E550",
        "#6ABE30",
        "#37946E",
        "#4B692F",
        "#524B24",
        "#323C39",
        "#3F3F74",
        "#306082",
        "#5B6EE1",
        "#639BFF",
        "#5FCDE4",
        "#CBDBFC",
        "#FFFFFF",
        "#9BADB7",
        "#847E87",
        "#696A6A",
        "#595652",
        "#76428A",
        "#AC3232",
        "#D95763",
        "#D77BBA",
        "#8F974A",
        "#8A6F30",
    ],
}


def _parse_hex_color(value: str) -> tuple[int, int, int] | None:
    """RGB-only parse (alpha dropped); unified via core.colors.parse_hex_color."""
    rgba = parse_hex_color(value)
    return rgba[:3] if rgba else None


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def get_palette(
    filename: Annotated[
        str, Field(description="Path to the Aseprite file to read the palette from")
    ],
) -> str:
    """Get the active sprite palette as a JSON array of hex colors."""
    if not await path_exists(filename):
        return f"File {filename} not found"

    script = """
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local ok, pal = pcall(function() return spr.palettes[1] end)
    if not ok or not pal then print("ERROR:No palette") return end

    local parts = {}
    local size = #pal
    table.insert(parts, "[")
    for i = 0, size - 1 do
        local c = pal:getColor(i)
        local hex = string.format("#%02X%02X%02X", c.red, c.green, c.blue)
        table.insert(parts, "\\"" .. hex .. "\\"")
        if i < size - 1 then
            table.insert(parts, ",")
        end
    end
    table.insert(parts, "]")
    print(table.concat(parts))
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return output
    return f"Failed to get palette: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_palette(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    colors: Annotated[
        list[str],
        Field(
            description="Full replacement palette as a list of #RRGGBB hex color strings"
        ),
    ],
) -> str:
    """Set the active sprite palette using a list of hex colors."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not colors:
        return "Colors list cannot be empty"

    rgb_list = []
    for color in colors:
        rgb = _parse_hex_color(color)
        if rgb is None:
            return "Colors must use #RRGGBB values"
        rgb_list.append(rgb)

    palette_entries = "\n".join(
        [
            f"    pal:setColor({i}, Color({r}, {g}, {b}))"
            for i, (r, g, b) in enumerate(rgb_list)
        ]
    )

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local pal = Palette({len(rgb_list)})
{palette_entries}
    spr:setPalette(pal)
    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Palette set with {len(colors)} colors in {filename}"
    return f"Failed to set palette: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def remap_colors_in_cel_range(
    filename: Annotated[str, Field(description="Path to the Aseprite file to modify")],
    layer_name: Annotated[
        str, Field(description="Name of the layer to remap colors in")
    ],
    start_frame: Annotated[
        int, Field(description="First frame index (1-based) to remap colors in")
    ],
    end_frame: Annotated[
        int, Field(description="Last frame index (1-based) to remap colors in")
    ],
    mappings: Annotated[
        list[dict[str, str]],
        Field(
            description=(
                "Color mappings to apply, each a dict with 'from' and 'to' "
                "#RRGGBB hex color strings"
            )
        ),
    ],
    create_missing_cels: Annotated[
        bool,
        Field(
            description="Create a cel (cloned from the source frame) where one is missing"
        ),
    ] = False,
    source_frame_index: Annotated[
        int | None,
        Field(
            description=(
                "Frame index to clone from when creating missing cels; "
                "defaults to start_frame when not given"
            )
        ),
    ] = None,
) -> str:
    """Remap colors in a layer across a frame range using explicit mappings."""
    if not await path_exists(filename):
        return f"File {filename} not found"
    if not mappings:
        return "Mappings list cannot be empty"

    parsed = []
    for m in mappings:
        src = _parse_hex_color(m.get("from") or "")
        dst = _parse_hex_color(m.get("to") or "")
        if src is None or dst is None:
            return "Mappings must use #RRGGBB colors"
        sr, sg, sb = src
        dr, dg, db = dst
        parsed.append((sr, sg, sb, dr, dg, db))

    mapping_lua = ", ".join(
        [f"{{{sr},{sg},{sb},{dr},{dg},{db}}}" for sr, sg, sb, dr, dg, db in parsed]
    )
    create_flag = "true" if create_missing_cels else "false"
    source_idx = "nil" if source_frame_index is None else str(source_frame_index)
    safe_layer_name = lua_escape(layer_name)

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    {FIND_LAYER}
    local target = find_layer(spr, "{safe_layer_name}")
    if not target then print("ERROR:Layer not found") return end

    local source_frame = {source_idx}
    if source_frame == nil then
        source_frame = start_idx
    end
    if source_frame < 1 or source_frame > #spr.frames then
        print("ERROR:Source frame out of range") return
    end

    local map = {{ {mapping_lua} }}

    app.transaction(function()
        for fi = start_idx, end_idx do
            local frame = spr.frames[fi]
            local cel = target:cel(frame)
            if not cel and {create_flag} then
                local source_cel = target:cel(spr.frames[source_frame])
                if source_cel then
                    local img = source_cel.image:clone()
                    cel = spr:newCel(target, frame, img, source_cel.position)
                else
                    local img = Image(spr.width, spr.height, spr.colorMode)
                    cel = spr:newCel(target, frame, img, Point(0, 0))
                end
            end
            if cel then
                local img = cel.image
                for y = 0, img.height - 1 do
                    for x = 0, img.width - 1 do
                        local c = img:getPixel(x, y)
                        local r = app.pixelColor.rgbaR(c)
                        local g = app.pixelColor.rgbaG(c)
                        local b = app.pixelColor.rgbaB(c)
                        local a = app.pixelColor.rgbaA(c)
                        if a > 0 then
                            for _, m in ipairs(map) do
                                if r == m[1] and g == m[2] and b == m[3] then
                                    local nc = app.pixelColor.rgba(m[4], m[5], m[6], a)
                                    img:putPixel(x, y, nc)
                                    break
                                end
                            end
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
        return f"Remapped colors on '{layer_name}' frames {start_frame}-{end_frame} in {filename}"
    return f"Failed to remap colors: {output}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def list_palette_presets() -> str:
    """List the built-in retro palette presets with their colors.

    Returns:
        JSON object mapping preset name to its list of hex colors.

    """
    return json.dumps(PALETTE_PRESETS, indent=2)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def apply_palette_preset(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    preset: Annotated[
        str,
        Field(
            description=(
                "Preset name: one of gameboy, monochrome, grayscale_4, cga, "
                "pico8, c64, dawnbringer16, dawnbringer32"
            )
        ),
    ],
) -> str:
    """Set the sprite palette to a built-in retro preset.

    This only sets the palette; existing pixels keep their colors.
    Use quantize_to_palette afterwards to snap pixels to the new palette.
    """
    colors = PALETTE_PRESETS.get(preset.lower())
    if colors is None:
        return f"Unknown preset '{preset}'. Available: {', '.join(sorted(PALETTE_PRESETS))}"
    result = await set_palette(filename, colors)
    if result.startswith("Palette set"):
        return f"Palette preset '{preset}' ({len(colors)} colors) applied to {filename}"
    return result


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def generate_color_ramp(
    base_color: Annotated[
        str, Field(description='Hex color the ramp is built around, e.g. "#D04648"')
    ],
    steps: Annotated[int, Field(description="Number of colors in the ramp, 2-16")] = 5,
    hue_shift_degrees: Annotated[
        float, Field(description="Total hue rotation across the ramp, in degrees")
    ] = 20,
    lightness_range: Annotated[
        float, Field(description="Total lightness span across the ramp, 0-1")
    ] = 0.5,
) -> str:
    """Generate a shading ramp (dark to light) from a base color.

    Produces the standard pixel-art shading technique of hue-shifting:
    shadows lean cooler (hue shifted one way), highlights lean warmer.
    Use the returned colors for shading instead of plain darker/lighter
    versions of the same hue.

    Returns:
        JSON array of hex colors ordered darkest to lightest.

    """
    rgb = _parse_hex_color(base_color)
    if rgb is None:
        return f"Invalid color value: {base_color}"
    if not (_RAMP_STEPS_MIN <= steps <= _RAMP_STEPS_MAX):
        return f"steps must be between {_RAMP_STEPS_MIN} and {_RAMP_STEPS_MAX}"
    if not (0 <= lightness_range <= 1):
        return "lightness_range must be between 0 and 1"

    r, g, b = (c / 255 for c in rgb)
    h, light, s = colorsys.rgb_to_hls(r, g, b)

    ramp = []
    mid = (steps - 1) / 2
    for i in range(steps):
        # t in [-0.5, 0.5]: negative = shadow side, positive = highlight side
        t = (i - mid) / (steps - 1) if steps > 1 else 0
        nh = (h - t * (hue_shift_degrees / 360)) % 1.0
        nl = min(1.0, max(0.0, light + t * lightness_range))
        # Shadows slightly more saturated, highlights slightly less
        ns = min(1.0, max(0.0, s - t * 0.15))
        nr, ng, nb = colorsys.hls_to_rgb(nh, nl, ns)
        ramp.append(f"#{round(nr * 255):02X}{round(ng * 255):02X}{round(nb * 255):02X}")
    return json.dumps(ramp)


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def quantize_to_palette(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    layer_name: Annotated[
        str,
        Field(description="Layer to quantize; empty string means all top-level layers"),
    ] = "",
    start_frame: Annotated[
        int, Field(description="First frame (1-based) to process")
    ] = 1,
    end_frame: Annotated[
        int,
        Field(description="Last frame (1-based) to process; 0 means the last frame"),
    ] = 0,
) -> str:
    """Snap every pixel to the nearest color in the sprite's palette.

    Walks the chosen cels and replaces each opaque pixel with the
    closest palette color (RGB distance). Run after apply_palette_preset
    or set_palette to make existing art conform to the palette. This is
    destructive: original colors that are not exact palette matches are
    permanently replaced.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"

    safe_layer = lua_escape(layer_name)
    script = f"""
    {FIND_LAYER}
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    local ok, pal = pcall(function() return spr.palettes[1] end)
    if not ok or not pal or #pal == 0 then print("ERROR:No palette") return end

    local start_idx = {start_frame}
    local end_idx = {end_frame}
    if end_idx < 1 then end_idx = #spr.frames end
    if start_idx < 1 or end_idx > #spr.frames or start_idx > end_idx then
        print("ERROR:Frame range out of bounds") return
    end

    local layers = {{}}
    if "{safe_layer}" ~= "" then
        local target = find_layer(spr, "{safe_layer}")
        if not target then print("ERROR:Layer not found") return end
        table.insert(layers, target)
    else
        for _, layer in ipairs(spr.layers) do
            if layer.isImage then table.insert(layers, layer) end
        end
    end

    local colors = {{}}
    for i = 0, #pal - 1 do
        local c = pal:getColor(i)
        table.insert(colors, {{c.red, c.green, c.blue}})
    end

    local cache = {{}}
    local function nearest(r, g, b)
        local key = r * 65536 + g * 256 + b
        local hit = cache[key]
        if hit then return hit end
        local best, best_d = colors[1], math.huge
        for _, c in ipairs(colors) do
            local dr, dg, db = r - c[1], g - c[2], b - c[3]
            local d = dr * dr + dg * dg + db * db
            if d < best_d then best, best_d = c, d end
        end
        cache[key] = best
        return best
    end

    local count = 0
    app.transaction(function()
        for _, layer in ipairs(layers) do
            for fi = start_idx, end_idx do
                local cel = layer:cel(spr.frames[fi])
                if cel then
                    local img = cel.image
                    for py = 0, img.height - 1 do
                        for px = 0, img.width - 1 do
                            local v = img:getPixel(px, py)
                            local a = app.pixelColor.rgbaA(v)
                            if a > 0 then
                                local r = app.pixelColor.rgbaR(v)
                                local g = app.pixelColor.rgbaG(v)
                                local b = app.pixelColor.rgbaB(v)
                                local c = nearest(r, g, b)
                                if c[1] ~= r or c[2] ~= g or c[3] ~= b then
                                    img:putPixel(px, py, app.pixelColor.rgba(c[1], c[2], c[3], a))
                                    count = count + 1
                                end
                            end
                        end
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
        return f"Failed to quantize: {output}"

    count = "?"
    for line in output.splitlines():
        if line.startswith("COUNT:"):
            count = line[len("COUNT:") :]
    return f"Quantized {count} pixels to the palette in {filename}"


@mcp.tool(
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def set_color_mode(
    filename: Annotated[str, Field(description="Aseprite file to modify")],
    mode: Annotated[
        str, Field(description='Target color mode: "rgb", "grayscale", or "indexed"')
    ],
) -> str:
    """Convert the sprite's color mode.

    Converting to "indexed" or "grayscale" can lose color information
    that is not exactly representable in the target mode.
    """
    if not await path_exists(filename):
        return f"File {filename} not found"
    if mode.lower() not in ("rgb", "grayscale", "indexed"):
        return "mode must be 'rgb', 'grayscale', or 'indexed'"

    script = f"""
    local spr = app.activeSprite
    if not spr then print("ERROR:No active sprite") return end

    app.command.ChangePixelFormat {{ format = "{mode.lower()}" }}

    spr:saveAs(spr.filename)
    print("OK")
    """

    success, output = AsepriteCommand.execute_lua_script_checked(script, filename)
    if success:
        return f"Color mode set to {mode} in {filename}"
    return f"Failed to set color mode: {output}"
