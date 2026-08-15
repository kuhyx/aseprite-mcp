#!/usr/bin/env python3
"""Composite Aseprite PNG exports onto dark and light backgrounds for review.

Post-processing only: every pixel comes from an already-exported Aseprite
file opened here. This script never synthesises art — it opens, composites
and tiles real exports so they can be judged against both background tones
(the item-icons skill requires checking outline readability on both).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

DARK = (30, 30, 38, 255)
LIGHT = (222, 222, 230, 255)
PAD = 8


def on_bg(img: Image.Image, rgba: tuple[int, int, int, int]) -> Image.Image:
    """Composite an RGBA export over a solid background."""
    bg = Image.new("RGBA", img.size, rgba)
    bg.alpha_composite(img)
    return bg


def main() -> None:
    """Write a dark|light side-by-side sheet of the given exports."""
    out = Path(sys.argv[1])
    paths = [Path(a) for a in sys.argv[2:]]
    shots = [Image.open(p).convert("RGBA") for p in paths]
    w = max(s.width for s in shots)
    h = max(s.height for s in shots)
    cols = len(shots)
    sheet = Image.new(
        "RGBA", (cols * (w + PAD) + PAD, 2 * (h + PAD) + PAD), (16, 16, 20, 255)
    )
    for i, s in enumerate(shots):
        x = PAD + i * (w + PAD)
        sheet.paste(on_bg(s, DARK), (x, PAD))
        sheet.paste(on_bg(s, LIGHT), (x, PAD + h + PAD))
    sheet.save(out)
    sys.stdout.write(f"wrote {out} ({sheet.width}x{sheet.height})\n")


if __name__ == "__main__":
    main()
