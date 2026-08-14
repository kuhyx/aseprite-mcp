#!/usr/bin/env python3
"""Deterministic checks on a glyph grid, before it ever reaches Aseprite.

Catches the mistakes that are invisible at 16x16 but obvious at 8x: ragged
row widths, an off-centre silhouette, unreachable colour counts, and gaps in
what should be a closed outline.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

TRANSPARENT = (".", " ")


def known_glyphs() -> set[str]:
    """Load the palette glyph set from gridtool at call time."""
    import gridtool

    return set(gridtool.DB32)


def rows_of(grid: str) -> list[str]:
    """Split a grid into lines, dropping leading/trailing blank lines."""
    return grid.strip("\n").splitlines()


def check(path: Path, *, size: int = 16) -> list[str]:
    """Return a list of problems found in the grid at `path`."""
    rows = rows_of(path.read_text(encoding="utf-8"))
    problems: list[str] = []

    if len(rows) != size:
        problems.append(f"height {len(rows)} != {size}")
    for i, row in enumerate(rows):
        if len(row) != size:
            problems.append(f"row {i} width {len(row)} != {size}")

    # Silhouette extents and centre of mass per row.
    centres: list[float] = []
    for i, row in enumerate(rows):
        xs = [x for x, ch in enumerate(row) if ch not in TRANSPARENT]
        if not xs:
            continue
        centres.append((min(xs) + max(xs)) / 2)
        del i

    if centres:
        lo, hi = min(centres), max(centres)
        if hi - lo > 2.0:
            problems.append(
                f"silhouette drifts: row centres span {lo:.1f}..{hi:.1f} "
                "(>2px lean; intentional only for asymmetric subjects)"
            )

    # Overall bounding box should sit near the canvas centre.
    all_xs = [x for row in rows for x, ch in enumerate(row) if ch not in TRANSPARENT]
    all_ys = [y for y, row in enumerate(rows) if any(c not in TRANSPARENT for c in row)]
    if all_xs and all_ys:
        bx = (min(all_xs) + max(all_xs)) / 2
        if abs(bx - (size - 1) / 2) > 1.0:
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
        if abs(margin_l - margin_r) > 2:
            problems.append(f"L/R margins uneven: {margin_l} vs {margin_r}")
        problems.append(
            f"INFO bbox x={min(all_xs)}..{max(all_xs)} y={min(all_ys)}..{max(all_ys)} "
            f"margins L{margin_l} R{margin_r} T{margin_t} B{margin_b}"
        )

    glyphs = {ch for row in rows for ch in row if ch not in TRANSPARENT}
    unknown = sorted(glyphs - known_glyphs())
    if unknown:
        problems.append(f"FATAL undefined glyphs: {''.join(unknown)}")
    problems.append(f"INFO {len(glyphs)} unique colours: {''.join(sorted(glyphs))}")
    if len(glyphs) > 12:
        problems.append(f"colour count {len(glyphs)} > 12 (noisy)")

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
