#!/usr/bin/env python3
"""Deterministic checks on a glyph grid, before it ever reaches Aseprite.

Catches the mistakes that are invisible at 16x16 but obvious at 8x: ragged
row widths, an off-centre silhouette, unreachable colour counts, and gaps in
what should be a closed outline.
"""

from __future__ import annotations

import sys
from pathlib import Path

# gridtool lives beside this file, not on the default path.
sys.path.insert(0, str(Path(__file__).parent))

import gridtool

TRANSPARENT = (".", " ")

# A row-centre span wider than this reads as a lean rather than a silhouette.
MAX_CENTRE_DRIFT = 2.0
# How far the bounding box may sit from the canvas centre.
MAX_BBOX_OFFSET = 1.0
# Left/right margins differing by more than this look lopsided.
MAX_MARGIN_SKEW = 2
# More colours than this stops reading as a coherent ramp.
MAX_COLOURS = 12


def known_glyphs() -> set[str]:
    """Return the palette glyph set defined by gridtool."""
    return set(gridtool.DB32)


def rows_of(grid: str) -> list[str]:
    """Split a grid into lines, dropping leading/trailing blank lines."""
    return grid.strip("\n").splitlines()


def _check_dimensions(rows: list[str], size: int) -> list[str]:
    """Report a wrong grid height or any row that is not `size` wide."""
    problems = []
    if len(rows) != size:
        problems.append(f"height {len(rows)} != {size}")
    problems += [
        f"row {i} width {len(row)} != {size}"
        for i, row in enumerate(rows)
        if len(row) != size
    ]
    return problems


def _check_silhouette_drift(rows: list[str]) -> list[str]:
    """Report a silhouette whose per-row centres lean off to one side."""
    centres = []
    for row in rows:
        xs = [x for x, ch in enumerate(row) if ch not in TRANSPARENT]
        if xs:
            centres.append((min(xs) + max(xs)) / 2)
    if not centres:
        return []
    lo, hi = min(centres), max(centres)
    if hi - lo > MAX_CENTRE_DRIFT:
        return [
            (
                f"silhouette drifts: row centres span {lo:.1f}..{hi:.1f} "
                "(>2px lean; intentional only for asymmetric subjects)"
            )
        ]
    return []


def _check_bounding_box(all_xs: list[int], all_ys: list[int], size: int) -> list[str]:
    """Report an off-centre box, edge contact, and uneven left/right margins."""
    problems = []
    bx = (min(all_xs) + max(all_xs)) / 2
    if abs(bx - (size - 1) / 2) > MAX_BBOX_OFFSET:
        problems.append(
            f"bbox x-centre {bx:.1f} is off-canvas-centre {(size - 1) / 2:.1f}"
        )
    margin_l, margin_r = min(all_xs), size - 1 - max(all_xs)
    margin_t, margin_b = min(all_ys), size - 1 - max(all_ys)
    # outline_cel writes into transparent neighbours; art touching an edge
    # gets no outline on that side, so every side needs >=1px of slack.
    touching = [
        side
        for side, m in (
            ("left", margin_l),
            ("right", margin_r),
            ("top", margin_t),
            ("bottom", margin_b),
        )
        if m == 0
    ]
    if touching:
        problems.append(
            f"FATAL touches canvas edge ({', '.join(touching)}) — "
            "outline_cel will be clipped there"
        )
    if abs(margin_l - margin_r) > MAX_MARGIN_SKEW:
        problems.append(f"L/R margins uneven: {margin_l} vs {margin_r}")
    problems.append(
        f"INFO bbox x={min(all_xs)}..{max(all_xs)} y={min(all_ys)}..{max(all_ys)} "
        f"margins L{margin_l} R{margin_r} T{margin_t} B{margin_b}"
    )
    return problems


def _check_palette(rows: list[str]) -> list[str]:
    """Report glyphs outside the known palette and an over-large colour count."""
    problems = []
    glyphs = {ch for row in rows for ch in row if ch not in TRANSPARENT}
    unknown = sorted(glyphs - known_glyphs())
    if unknown:
        problems.append(f"FATAL undefined glyphs: {''.join(unknown)}")
    problems.append(f"INFO {len(glyphs)} unique colours: {''.join(sorted(glyphs))}")
    if len(glyphs) > MAX_COLOURS:
        problems.append(f"colour count {len(glyphs)} > {MAX_COLOURS} (noisy)")
    return problems


def check(path: Path, *, size: int = 16) -> list[str]:
    """Return a list of problems found in the grid at `path`."""
    rows = rows_of(path.read_text(encoding="utf-8"))
    problems = _check_dimensions(rows, size)
    problems += _check_silhouette_drift(rows)

    all_xs = [x for row in rows for x, ch in enumerate(row) if ch not in TRANSPARENT]
    all_ys = [y for y, row in enumerate(rows) if any(c not in TRANSPARENT for c in row)]
    if all_xs and all_ys:
        problems += _check_bounding_box(all_xs, all_ys, size)

    problems += _check_palette(rows)

    filled = len(all_xs)
    problems.append(
        f"INFO {filled} opaque pixels ({filled * 100 // (size * size)}% fill)"
    )
    return problems


def main() -> None:
    """Check every grid path given on the command line."""
    for arg in sys.argv[1:]:
        p = Path(arg)
        sys.stdout.write(f"\n=== {p.name} ===\n")
        for line in check(p):
            sys.stdout.write(f"  {line}\n")


if __name__ == "__main__":
    main()
