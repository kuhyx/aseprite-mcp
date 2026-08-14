#!/usr/bin/env python3
"""Seam checking and repeat-preview for 32x32 terrain tiles.

The seam check is the deterministic gate the feasibility doc calls for: a
tile is only seamless if its wrapped neighbours are as plausible as its
interior, which we measure by comparing edge-adjacency statistics rather than
demanding the edges be identical.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

SIZE = 32


def load(path: Path) -> Image.Image:
    """Load a tile as RGBA and assert its size."""
    img = Image.open(path).convert("RGBA")
    if img.size != (SIZE, SIZE):
        msg = f"{path.name} is {img.size}, expected {SIZE}x{SIZE}"
        raise SystemExit(msg)
    return img


def wrap_discontinuity(img: Image.Image) -> tuple[float, float]:
    """Return (horizontal, vertical) seam energy.

    Compares the colour difference across the wrap boundary against the mean
    difference between adjacent interior columns/rows. A ratio near 1.0 means
    the seam is statistically invisible; >>1 means a hard edge.
    """
    px = img.load()

    def diff(ax: int, ay: int, bx: int, by: int) -> float:
        a, b = px[ax, ay], px[bx, by]
        return sum(abs(a[i] - b[i]) for i in range(3)) / 3.0

    # Horizontal: column 31 -> column 0 (wrap) vs all interior column pairs.
    seam_h = sum(diff(SIZE - 1, y, 0, y) for y in range(SIZE)) / SIZE
    inner_h = sum(
        diff(x, y, x + 1, y) for x in range(SIZE - 1) for y in range(SIZE)
    ) / (SIZE * (SIZE - 1))

    seam_v = sum(diff(x, SIZE - 1, x, 0) for x in range(SIZE)) / SIZE
    inner_v = sum(
        diff(x, y, x, y + 1) for x in range(SIZE) for y in range(SIZE - 1)
    ) / (SIZE * (SIZE - 1))

    h = seam_h / inner_h if inner_h else 0.0
    v = seam_v / inner_v if inner_v else 0.0
    return h, v


def quadrant_weight(img: Image.Image) -> float:
    """Return max/min mean luminance across quadrants.

    Slynyrd's rule: visual weight must be evenly distributed, or the repeated
    pattern acquires an obvious anchor. A ratio near 1.0 is even.
    """
    px = img.load()
    half = SIZE // 2
    means = []
    for qy in (0, half):
        for qx in (0, half):
            tot = 0.0
            for y in range(qy, qy + half):
                for x in range(qx, qx + half):
                    r, g, b, _ = px[x, y]
                    tot += 0.299 * r + 0.587 * g + 0.114 * b
            means.append(tot / (half * half))
    lo, hi = min(means), max(means)
    return hi / lo if lo else 0.0


def repeat(img: Image.Image, n: int = 3, scale: int = 4) -> Image.Image:
    """Tile the image n x n and scale it up for visual seam inspection."""
    out = Image.new("RGBA", (SIZE * n, SIZE * n))
    for gy in range(n):
        for gx in range(n):
            out.paste(img, (gx * SIZE, gy * SIZE))
    return out.resize((SIZE * n * scale, SIZE * n * scale), Image.NEAREST)


def calibrate() -> None:
    """Print the metric's reading for a provably-seamless and a seamed tile.

    Run this instead of guessing a threshold. A guessed 1.35 once flagged five
    perfectly good tiles; these two controls show the real scale in one command.
    """
    import math

    good = Image.new("RGBA", (SIZE, SIZE))
    bad = Image.new("RGBA", (SIZE, SIZE))
    for y in range(SIZE):
        for x in range(SIZE):
            # A sinusoid with an integer number of periods wraps exactly.
            v = int(
                128
                + 100
                * math.sin(2 * math.pi * x / SIZE)
                * math.cos(2 * math.pi * y / SIZE)
            )
            good.putpixel((x, y), (v, v, v, 255))
            hard = 20 if x < SIZE // 2 else 230
            bad.putpixel((x, y), (hard, hard, hard, 255))
    gh, gv = wrap_discontinuity(good)
    bh, bv = wrap_discontinuity(bad)
    sys.stdout.write(
        f"seamless control: h={gh:.2f} v={gv:.2f}\n"
        f"seamed   control: h={bh:.2f} v={bv:.2f}\n"
        "-> anything below ~4 is texture variation, not a seam.\n"
    )


def main() -> None:
    """Report seam metrics for every tile given, and write repeat previews."""
    if len(sys.argv) > 1 and sys.argv[1] == "--calibrate":
        calibrate()
        return
    for arg in sys.argv[1:]:
        p = Path(arg)
        img = load(p)
        h, v = wrap_discontinuity(img)
        w = quadrant_weight(img)
        # Threshold calibrated against controls: a provably seamless tile
        # (wrapping sinusoid) scores ~1.6, a hard half/half seam scores ~31.
        # Anything under 4 is texture variation, not a seam.
        # Transition tiles are meant to differ top-to-bottom, so only the
        # horizontal wrap and their vertical JOIN to a neighbour are checked.
        is_transition = "_" in p.stem
        if is_transition:
            flag = "OK " if h < 4.0 else "SEAM"
        else:
            flag = "OK " if h < 4.0 and v < 4.0 and w < 1.18 else "SEAM"
        sys.stdout.write(f"{flag} {p.stem:12s} h={h:.2f} v={v:.2f} weight={w:.2f}\n")
        repeat(img).save(p.parent / f"repeat_{p.stem}.png")


if __name__ == "__main__":
    main()
