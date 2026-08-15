#!/usr/bin/env python3
"""Author the 32x32 terrain tiles as hand-placed, wrapping pixel clusters.

Every cluster below is a hand-chosen (x, y) with a hand-chosen shape. Writes
wrap around the tile edges by construction, which is what makes the result
seamless and is the reason clusters are placed rather than sampled from noise.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

SIZE = 32

# dawnbringer32 subsets, three values per material (shadow / base / light).
GRASS = ("#4B692F", "#6ABE30", "#99E550")
DIRT = ("#45283C", "#663931", "#8F563B")
STONE = ("#323C39", "#696A6A", "#9BADB7")
SAND = ("#8A6F30", "#D9A066", "#EEC39A")
WATER = ("#306082", "#5B6EE1", "#639BFF")


def blank(color: str) -> Image.Image:
    """Return a tile filled with the given base colour."""
    return Image.new("RGBA", (SIZE, SIZE), color)


def put(img: Image.Image, x: int, y: int, color: str) -> None:
    """Set one pixel, wrapping coordinates around the tile."""
    img.putpixel(
        (x % SIZE, y % SIZE), Image.new("RGBA", (1, 1), color).getpixel((0, 0))
    )


def cluster(
    img: Image.Image, x: int, y: int, shape: list[tuple[int, int]], color: str
) -> None:
    """Stamp a hand-defined cluster at (x, y), wrapping at the edges."""
    for dx, dy in shape:
        put(img, x + dx, y + dy, color)


# Hand-drawn cluster shapes, small and irregular so no single one dominates.
BLADE = [(0, 0), (0, -1), (0, -2)]
TUFT = [(0, 0), (1, 0), (0, -1), (2, -1), (1, -2)]
SPECK = [(0, 0)]
PEBBLE = [(0, 0), (1, 0), (0, 1), (1, 1)]
CRACK = [(0, 0), (1, 1), (2, 1), (3, 2)]
RIPPLE = [(0, 0), (1, 0), (2, 0), (3, 0)]
RIPPLE2 = [(0, 0), (1, 0)]
RIPPLE3 = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1)]


def grass() -> Image.Image:
    """Grass: dense short blades, a few darker patches, occasional highlight."""
    img = blank(GRASS[1])
    # Dark tufts, spread so each quadrant carries similar weight, several
    # deliberately straddling the edges.
    for x, y in [
        (3, 5),
        (11, 2),
        (19, 7),
        (27, 4),
        (30, 12),
        (6, 14),
        (14, 11),
        (22, 16),
        (1, 20),
        (9, 24),
        (17, 27),
        (25, 22),
        (29, 29),
        (5, 30),
        (13, 18),
        (21, 31),
        (0, 9),
        (31, 25),
    ]:
        cluster(img, x, y, TUFT, GRASS[0])
    # Light blades, offset from the dark ones so values interleave.
    for x, y in [
        (7, 3),
        (15, 6),
        (23, 2),
        (31, 8),
        (2, 12),
        (10, 16),
        (18, 13),
        (26, 19),
        (4, 23),
        (12, 28),
        (20, 25),
        (28, 30),
        (6, 8),
        (16, 21),
        (24, 9),
        (0, 27),
    ]:
        cluster(img, x, y, BLADE, GRASS[2])
    return img


def dirt() -> Image.Image:
    """Dirt: fine speckle plus a few small stones, no dominant feature."""
    img = blank(DIRT[1])
    for x, y in [
        (2, 3),
        (9, 1),
        (16, 6),
        (24, 2),
        (30, 9),
        (5, 11),
        (13, 8),
        (21, 13),
        (28, 17),
        (3, 18),
        (11, 21),
        (19, 19),
        (26, 25),
        (7, 27),
        (15, 30),
        (23, 28),
        (31, 31),
        (0, 14),
        (18, 24),
        (10, 13),
    ]:
        cluster(img, x, y, SPECK, DIRT[0])
    for x, y in [(6, 5), (20, 9), (12, 17), (27, 21), (1, 25), (16, 2), (30, 28)]:
        cluster(img, x, y, PEBBLE, DIRT[2])
    for x, y in [(8, 14), (22, 4), (4, 29), (25, 13)]:
        cluster(img, x, y, SPECK, DIRT[2])
    # Clods: small irregular dark patches that give the surface relief.
    clod = [(0, 0), (1, 0), (2, 1), (1, 1)]
    for x, y in [
        (5, 7),
        (17, 4),
        (27, 11),
        (9, 19),
        (21, 23),
        (31, 3),
        (1, 30),
        (14, 26),
        (24, 30),
        (12, 11),
    ]:
        cluster(img, x, y, clod, DIRT[0])
    return img


def stone() -> Image.Image:
    """Stone: cobbled blocks with mortar lines that wrap cleanly."""
    img = blank(STONE[1])
    # Mortar grid, offset per row so the pattern is masonry, not a checkerboard.
    for y in (0, 8, 16, 24):
        for x in range(SIZE):
            put(img, x, y, STONE[0])
    offsets = {0: 0, 8: 12, 16: 6, 24: 18}
    for y, off in offsets.items():
        for x in (off, off + 16):
            for dy in range(1, 8):
                put(img, x, y + dy, STONE[0])
    # Light catch on the top-left of each block face.
    for y, off in offsets.items():
        for x in (off, off + 16):
            for dx in range(1, 15):
                put(img, x + dx, y + 1, STONE[2])
    for x, y in [(4, 4), (20, 12), (10, 20), (26, 28)]:
        cluster(img, x, y, CRACK, STONE[0])
    return img


def sand() -> Image.Image:
    """Sand: gentle wave lines, broken so they don't read as ramen noodles."""
    img = blank(SAND[1])
    for x, y in [
        (0, 4),
        (10, 6),
        (20, 3),
        (28, 7),
        (5, 12),
        (15, 14),
        (24, 11),
        (2, 19),
        (12, 22),
        (21, 18),
        (29, 23),
        (7, 27),
        (17, 30),
        (26, 26),
    ]:
        shapes = (RIPPLE, RIPPLE2, RIPPLE3)
        cluster(img, x, y, shapes[(x + y) % 3], SAND[0])
    for x, y in [
        (6, 2),
        (16, 9),
        (26, 5),
        (1, 15),
        (11, 17),
        (22, 15),
        (30, 19),
        (4, 24),
        (14, 26),
        (23, 30),
        (9, 9),
        (19, 24),
    ]:
        cluster(img, x, y, SPECK, SAND[2])
    return img


def water() -> Image.Image:
    """Water: horizontal ripple bands with light crests, evenly spread."""
    img = blank(WATER[1])
    for x, y in [
        (0, 3),
        (9, 5),
        (18, 2),
        (27, 6),
        (4, 10),
        (13, 12),
        (22, 9),
        (30, 13),
        (2, 17),
        (11, 19),
        (20, 16),
        (28, 20),
        (6, 24),
        (15, 26),
        (24, 23),
        (31, 28),
        (8, 30),
        (17, 29),
    ]:
        shapes = (RIPPLE, RIPPLE3, RIPPLE2)
        cluster(img, x, y, shapes[(x + y) % 3], WATER[0])
    for x, y in [
        (5, 1),
        (14, 7),
        (23, 4),
        (31, 10),
        (7, 14),
        (16, 21),
        (25, 18),
        (1, 22),
        (10, 27),
        (19, 31),
        (28, 25),
        (3, 7),
    ]:
        shapes = (RIPPLE2, RIPPLE, RIPPLE2)
        cluster(img, x, y, shapes[(x * 2 + y) % 3], WATER[2])
    return img


TILES = {
    "grass": grass,
    "dirt": dirt,
    "stone": stone,
    "sand": sand,
    "water": water,
}


def main() -> None:
    """Write every tile (or those named) as a PNG."""
    out = Path(__file__).parent
    names = sys.argv[1:] or list(TILES)
    for n in names:
        img = TILES[n]()
        img.save(out / f"{n}.png")
        sys.stdout.write(f"wrote {n}.png\n")


def _irregular_edge(seed_row: list[int]) -> list[int]:
    """Return a hand-authored per-column depth profile for an organic boundary."""
    return seed_row


# Hand-picked depth profiles: how far the top terrain intrudes, per column.
# Irregular by design so the boundary doesn't read as a ruled line.
GRASS_DIRT_EDGE = [
    14,
    15,
    15,
    16,
    16,
    15,
    14,
    14,
    13,
    14,
    15,
    16,
    17,
    17,
    16,
    15,
    15,
    16,
    16,
    17,
    16,
    15,
    14,
    13,
    13,
    14,
    15,
    15,
    16,
    16,
    15,
    14,
]
SAND_WATER_EDGE = [
    16,
    16,
    17,
    18,
    18,
    17,
    16,
    16,
    15,
    15,
    16,
    17,
    18,
    18,
    17,
    16,
    16,
    15,
    15,
    16,
    17,
    17,
    18,
    17,
    16,
    15,
    15,
    16,
    16,
    17,
    17,
    16,
]
GRASS_SAND_EDGE = [
    15,
    16,
    16,
    15,
    14,
    14,
    15,
    16,
    17,
    17,
    16,
    15,
    15,
    14,
    14,
    15,
    16,
    17,
    17,
    16,
    15,
    14,
    14,
    15,
    16,
    16,
    17,
    16,
    15,
    15,
    14,
    15,
]


def transition(
    top: Image.Image, bottom: Image.Image, depth: list[int], fringe: str | None = None
) -> Image.Image:
    """Composite `top` over `bottom` along a hand-authored depth profile.

    Both textures keep their own identity because each pixel comes from a real
    tile, which is the subtractive method the references describe.
    """
    out = bottom.copy()
    for x in range(SIZE):
        for y in range(depth[x]):
            out.putpixel((x, y), top.getpixel((x, y)))
        if fringe is not None:
            out.putpixel(
                (x, depth[x]), Image.new("RGBA", (1, 1), fringe).getpixel((0, 0))
            )
    return out


def grass_dirt() -> Image.Image:
    """Grass above, dirt below, with a dark soil lip at the boundary."""
    return transition(grass(), dirt(), GRASS_DIRT_EDGE, DIRT[0])


def sand_water() -> Image.Image:
    """Sand above, water below, with a pale foam line at the waterline."""
    return transition(sand(), water(), SAND_WATER_EDGE, SAND[2])


def grass_sand() -> Image.Image:
    """Grass above, sand below, blended without a hard lip."""
    return transition(grass(), sand(), GRASS_SAND_EDGE, None)


TILES.update(
    {
        "grass_dirt": grass_dirt,
        "sand_water": sand_water,
        "grass_sand": grass_sand,
    }
)


if __name__ == "__main__":
    main()


def water_frame(shift: int) -> Image.Image:
    """One frame of the water loop.

    The crests advance by `shift` px and the trough pattern moves the opposite
    way, which reads as flow rather than the whole texture sliding sideways.
    """
    img = blank(WATER[1])
    for x, y in [
        (0, 3),
        (9, 5),
        (18, 2),
        (27, 6),
        (4, 10),
        (13, 12),
        (22, 9),
        (30, 13),
        (2, 17),
        (11, 19),
        (20, 16),
        (28, 20),
        (6, 24),
        (15, 26),
        (24, 23),
        (31, 28),
        (8, 30),
        (17, 29),
    ]:
        shapes = (RIPPLE, RIPPLE3, RIPPLE2)
        cluster(img, x + shift, y, shapes[(x + y) % 3], WATER[0])
    for x, y in [
        (5, 1),
        (14, 7),
        (23, 4),
        (31, 10),
        (7, 14),
        (16, 21),
        (25, 18),
        (1, 22),
        (10, 27),
        (19, 31),
        (28, 25),
        (3, 7),
    ]:
        shapes = (RIPPLE2, RIPPLE, RIPPLE2)
        cluster(img, x - shift, y, shapes[(x * 2 + y) % 3], WATER[2])
    return img


def water_frames() -> list[Image.Image]:
    """Four frames spanning a full 32px cycle.

    Shifts of 0/8/16/24 make the wrap from the last frame back to the first
    exactly one more 8px step, so the loop closes with no pop.
    """
    return [water_frame(s) for s in (0, 8, 16, 24)]
