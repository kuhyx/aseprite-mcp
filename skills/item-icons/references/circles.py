#!/usr/bin/env python3
"""Generate and gate pixel circles by the run-length delta rule.

A circle reads as round when its row-run-lengths grow with deltas that
decrease monotonically to zero (2,2,2,0,0). A stutter (4,2,0,2) puts a flat
spot mid-arc followed by a re-widening, which the eye reads as "squashed".
Aseprite's own filled-ellipse stutters at d=12/14/15/16, so the shapes here
are generated with a distance threshold and then gated, never taken on trust.
"""

from __future__ import annotations

import sys


def rows_threshold(d: int, eps: float = 0.0) -> list[int]:
    """Row run-lengths for a circle of diameter d, biased outward by eps."""
    r = d / 2.0
    out: list[int] = []
    for y in range(d):
        cy = y + 0.5 - r
        n = sum(1 for x in range(d) if (x + 0.5 - r) ** 2 + cy * cy <= (r + eps) ** 2)
        out.append(n)
    return out


def deltas(runs: list[int]) -> list[int]:
    """First differences across the top half of the run-length sequence."""
    half = (len(runs) + 1) // 2
    return [runs[i + 1] - runs[i] for i in range(half - 1)]


def is_round(runs: list[int]) -> bool:
    """True when deltas are non-increasing and never re-widen after a hold."""
    ds = deltas(runs)
    if any(x < 0 for x in ds):
        return False
    return all(ds[i] >= ds[i + 1] for i in range(len(ds) - 1))


def best_eps(d: int) -> tuple[float, list[int]]:
    """Pick the smallest eps whose circle passes the delta gate."""
    for eps in (0.0, 0.25, 0.5, 0.75):
        runs = rows_threshold(d, eps)
        if is_round(runs) and runs[0] > 0:
            return eps, runs
    msg = f"no eps produced a round circle for d={d}"
    raise SystemExit(msg)


def render(runs: list[int], size: int, ox: int, oy: int, ch: str = "#") -> list[str]:
    """Render run-lengths as centred rows of `ch` on a size x size grid."""
    grid = [["." for _ in range(size)] for _ in range(size)]
    for i, n in enumerate(runs):
        y = oy + i
        if not 0 <= y < size:
            continue
        start = ox - n // 2
        for x in range(start, start + n):
            if 0 <= x < size:
                grid[y][x] = ch
    return ["".join(r) for r in grid]


def main() -> None:
    """Print gated circle patterns for the diameters given."""
    for arg in sys.argv[1:] or ["10", "11", "12", "13"]:
        d = int(arg)
        aseprite = rows_threshold(d, 0.0)
        eps, runs = best_eps(d)
        sys.stdout.write(
            f"\nd={d}\n"
            f"  eps=0.00 (≈Aseprite): {aseprite} deltas={deltas(aseprite)} "
            f"{'round' if is_round(aseprite) else 'STUTTER'}\n"
            f"  eps={eps:.2f} (picked):  {runs} deltas={deltas(runs)} round\n"
        )
        for line in render(runs, d, d // 2, 0):
            sys.stdout.write("    " + line + "\n")


if __name__ == "__main__":
    main()
