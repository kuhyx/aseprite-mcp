#!/usr/bin/env python3
"""Render glyph grids to a big PNG so the shape can be judged by eye.

This is a *preview* of hand-authored grids, not a generator: it never invents
pixels. It exists so a bad silhouette is caught before any MCP calls are spent.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from gridtool import grid_to_pixels

SCALE = 16
PAD = 8
LABEL_H = 14


def render_one(path: Path, size: int = 16) -> Image.Image:
    """Render a single grid file to a scaled RGBA image."""
    img = Image.new("RGBA", (size * SCALE, size * SCALE), (30, 30, 38, 255))
    d = ImageDraw.Draw(img)
    for px in grid_to_pixels(path.read_text(encoding="utf-8")):
        x, y = int(px["x"]), int(px["y"])
        d.rectangle(
            [x * SCALE, y * SCALE, (x + 1) * SCALE - 1, (y + 1) * SCALE - 1],
            fill=str(px["color"]),
        )
    return img


def main() -> None:
    """Render every grid given on the command line into one contact sheet."""
    out = Path(sys.argv[1])
    paths = [Path(a) for a in sys.argv[2:]]
    cols = min(4, len(paths))
    rows = (len(paths) + cols - 1) // cols
    cw, ch = 16 * SCALE + PAD * 2, 16 * SCALE + PAD * 2 + LABEL_H
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (22, 22, 28, 255))
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(paths):
        cx, cy = (i % cols) * cw, (i // cols) * ch
        sheet.paste(render_one(p), (cx + PAD, cy + PAD + LABEL_H))
        d.text((cx + PAD, cy + 2), p.stem, fill=(200, 200, 210, 255))
    sheet.save(out)
    sys.stdout.write(f"wrote {out} ({sheet.width}x{sheet.height})\n")


if __name__ == "__main__":
    main()
