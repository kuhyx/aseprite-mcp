#!/usr/bin/env python3
"""Turn a hand-authored ASCII glyph grid into draw_pixels_at JSON.

The grid is authored by hand, one character per pixel; this only translates
characters to hex colors so the MCP call can consume it. Keeping the art in a
readable grid is what makes it reviewable and editable pixel by pixel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Verified dawnbringer32 values, read back from Aseprite via get_palette.
DB32 = {
    "k": "#000000",  # pure black
    "o": "#222034",  # outline / darkest
    "p": "#45283C",  # deep plum shadow
    "w": "#663931",  # wood shadow
    "W": "#8F563B",  # wood base
    "r": "#DF7126",  # orange
    "t": "#D9A066",  # tan / light wood
    "T": "#EEC39A",  # pale skin/paper
    "y": "#FBF236",  # yellow highlight
    "g": "#99E550",  # light green
    "G": "#6ABE30",  # green
    "e": "#37946E",  # teal green
    "E": "#4B692F",  # dark green
    "v": "#524B24",  # olive shadow
    "V": "#323C39",  # dark slate
    "n": "#3F3F74",  # navy
    "b": "#306082",  # deep blue
    "B": "#5B6EE1",  # blue
    "L": "#639BFF",  # light blue
    "c": "#5FCDE4",  # cyan
    "C": "#CBDBFC",  # pale ice
    "1": "#FFFFFF",  # white
    "s": "#9BADB7",  # steel light
    "S": "#847E87",  # steel mid
    "d": "#696A6A",  # grey
    "D": "#595652",  # dark grey
    "u": "#76428A",  # purple
    "R": "#AC3232",  # red
    "P": "#D95763",  # pink red
    "m": "#D77BBA",  # magenta
    "a": "#8F974A",  # olive light
    "A": "#8A6F30",  # dark gold
}


def grid_to_pixels(grid: str, ox: int = 0, oy: int = 0) -> list[dict[str, object]]:
    """Convert a glyph grid to a pixel list. '.' and ' ' mean transparent."""
    pixels: list[dict[str, object]] = []
    for y, line in enumerate(grid.strip("\n").splitlines()):
        for x, ch in enumerate(line):
            if ch in (".", " "):
                continue
            if ch not in DB32:
                msg = f"unknown glyph {ch!r} at ({x},{y})"
                raise ValueError(msg)
            pixels.append({"x": x + ox, "y": y + oy, "color": DB32[ch]})
    return pixels


def main() -> None:
    """Read a grid file and emit the pixel JSON payload."""
    # argv: <grid> [origin_x] [origin_y]
    argc_with_ox = 3
    argc_with_oy = 4
    src = Path(sys.argv[1])
    ox = int(sys.argv[2]) if len(sys.argv) >= argc_with_ox else 0
    oy = int(sys.argv[3]) if len(sys.argv) >= argc_with_oy else 0
    px = grid_to_pixels(src.read_text(encoding="utf-8"), ox, oy)
    sys.stdout.write(json.dumps(px))


if __name__ == "__main__":
    main()
