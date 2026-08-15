#!/usr/bin/env python3
"""Fail-closed gates for the icon animations.

Every check here operates on real Aseprite exports opened from disk — this
module never synthesises pixels. It exists because the built-in checks lie:
`audit_animation` reports "clean" on four identical frames, and several MCP
tools reported success having drawn nothing (fixed 2026-08-15; see tofix.md).

Gates, all hard failures (exit 1) per the user's instruction:

  margins   opaque ink must keep >= N px of clear border on every side, so
            `outline_cel` is never clipped and a 1px bob cannot eat it.
  motion    every adjacent GIF frame pair must differ, WRAP INCLUDED,
            compared on composited RGBA (not palette bytes, which
            reindexing makes falsely differ).
  wrap      the last->first step must equal the interior steps exactly
            (ratio 1.0), or the loop visibly pops.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageSequence

MIN_FRAMES = 2
DEFAULT_MARGIN = 2

# Ratio comparisons use an epsilon: equal steps can divide to 1.0000000000000002,
# which would fail a bare `> 1.0` and reject a mathematically perfect loop.
RATIO_EPS = 1e-9


class GateError(Exception):
    """A gate rejected the artwork."""


def frames_rgba(path: Path) -> list[Image.Image]:
    """Every frame of a GIF as full composited RGBA images."""
    with Image.open(path) as src:
        return [f.convert("RGBA").copy() for f in ImageSequence.Iterator(src)]


def ink_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """Bounding box of non-transparent pixels as (x0, y0, x1, y1)."""
    box = img.getchannel("A").getbbox()
    if box is None:
        msg = "frame is entirely transparent"
        raise GateError(msg)
    x0, y0, x1, y1 = box
    return x0, y0, x1 - 1, y1 - 1


def check_margins(img: Image.Image, need: int, label: str) -> list[str]:
    """Require `need` px of clear border on all four sides."""
    x0, y0, x1, y1 = ink_bbox(img)
    left, top = x0, y0
    right, bottom = img.width - 1 - x1, img.height - 1 - y1
    bad = [
        f"{side}={m}"
        for side, m in (
            ("L", left),
            ("R", right),
            ("T", top),
            ("B", bottom),
        )
        if m < need
    ]
    if bad:
        msg = f"{label}: margin < {need}px ({', '.join(bad)}) — outline will clip"
        raise GateError(msg)
    return [f"{label}: margins L{left} R{right} T{top} B{bottom} >= {need} OK"]


def check_motion(frames: list[Image.Image], label: str) -> list[str]:
    """Every adjacent pair must differ, including the wrap back to frame 1."""
    if len(frames) < MIN_FRAMES:
        msg = f"{label}: {len(frames)} frame(s) — not an animation"
        raise GateError(msg)
    data = [f.tobytes() for f in frames]
    n = len(data)
    same = [
        f"{i + 1}->{(i + 1) % n + 1}" for i in range(n) if data[i] == data[(i + 1) % n]
    ]
    if same:
        msg = f"{label}: identical adjacent frames {', '.join(same)} — static animation"
        raise GateError(msg)
    return [f"{label}: all {n} adjacent pairs differ (wrap included) OK"]


def check_distinct(frames: list[Image.Image], label: str, need: int) -> list[str]:
    """Require at least `need` distinct frames in the loop.

    `check_motion` only compares ADJACENT pairs, so an `A,B,A,B` sequence —
    a 2-frame flicker padded out to 4 — passes it while frames 1 and 3 are
    byte-identical. Verified: that exact case passed both check_motion and
    check_oscillation before this gate existed.

    `need` is not always the frame count. A symmetric 1px bob (0,-1,-2,-1)
    legitimately revisits a height, giving 3 distinct frames out of 4 — that
    is what a bob IS, not a padded loop. Demand 3 there and 4 for travelling
    motion, rather than forcing the art to satisfy the metric.
    """
    n = len(frames)
    uniq = len({f.tobytes() for f in frames})
    if uniq < need:
        msg = (
            f"{label}: only {uniq} distinct frames out of {n} "
            f"(need >= {need}) — padded loop"
        )
        raise GateError(msg)
    return [f"{label}: {uniq}/{n} frames distinct (need >= {need}) OK"]


def centroid(img: Image.Image) -> tuple[float, float]:
    """Alpha-weighted centre of mass of a frame."""
    alpha = img.getchannel("A")
    tot = sx = sy = 0
    for y in range(img.height):
        for x in range(img.width):
            a = alpha.getpixel((x, y))
            if a:
                tot += a
                sx += x * a
                sy += y * a
    if not tot:
        msg = "frame is entirely transparent"
        raise GateError(msg)
    return sx / tot, sy / tot


def best_shift(a: Image.Image, b: Image.Image) -> tuple[int, int]:
    """Find the wrapped (dx, dy) that best aligns frame `a` onto frame `b`.

    A full-bleed tile has no transparency, so the alpha centroid is dead
    centre in every frame and measures zero motion even when the texture
    clearly scrolls. Matching the actual pixels is what works there.
    """
    ga, gb = a.convert("L"), b.convert("L")
    w, h = ga.size
    pa, pb = ga.load(), gb.load()
    best, bxy = None, (0, 0)
    for dy in range(h):
        for dx in range(w):
            err = sum(
                abs(pa[x, y] - pb[(x + dx) % w, (y + dy) % h])
                for y in range(0, h, 2)
                for x in range(0, w, 2)
            )
            if best is None or err < best:
                best, bxy = err, (dx, dy)
    return bxy


def check_tile_flow(frames: list[Image.Image], label: str, tol: float) -> list[str]:
    """Opaque scrolling tiles: every frame-to-frame shift must be equal."""
    n = len(frames)
    shifts = [best_shift(frames[i], frames[(i + 1) % n]) for i in range(n)]
    mags = [(dx * dx + dy * dy) ** 0.5 for dx, dy in shifts]
    lo, hi = min(mags), max(mags)
    if lo <= 0:
        msg = f"{label}: a step has zero shift {shifts} — frame did not move"
        raise GateError(msg)
    ratio = hi / lo
    if ratio > tol + RATIO_EPS:
        msg = f"{label}: shift ratio {ratio:.3f} > {tol} shifts={shifts} — loop pops"
        raise GateError(msg)
    return [f"{label}: equal shifts {shifts} (ratio {ratio:.3f}) OK"]


def _signed_wrapped(delta: float, span: int) -> float:
    """Shortest signed displacement, accounting for wrap around `span`."""
    d = delta % span
    return d - span if d > span / 2 else d


def check_wrap_ratio(frames: list[Image.Image], label: str, tol: float) -> list[str]:
    """Interior and wrap steps must be equal within `tol` (user asked 1.0).

    Travelling motion (a glint sweeping across the object) wraps: the last
    frame steps forward into the first, so displacement is measured modulo
    the canvas. A 4-position glint on an OPEN path gives a 3x reverse jump
    here and is rejected — the band must wrap by construction.
    """
    cs = [centroid(f) for f in frames]
    n = len(cs)
    w, h = frames[0].width, frames[0].height
    steps = [
        (
            _signed_wrapped(cs[(i + 1) % n][0] - cs[i][0], w) ** 2
            + _signed_wrapped(cs[(i + 1) % n][1] - cs[i][1], h) ** 2
        )
        ** 0.5
        for i in range(n)
    ]
    lo, hi = min(steps), max(steps)
    if lo <= 0:
        msg = f"{label}: a step has zero displacement {[round(s, 3) for s in steps]}"
        raise GateError(msg)
    ratio = hi / lo
    if ratio > tol + RATIO_EPS:
        msg = (
            f"{label}: wrap ratio {ratio:.3f} > {tol} "
            f"steps={[round(s, 2) for s in steps]} — loop pops"
        )
        raise GateError(msg)
    return [
        f"{label}: step ratio {ratio:.3f} <= {tol} steps={[round(s, 2) for s in steps]} OK"
    ]


def check_oscillation(frames: list[Image.Image], label: str, tol: float) -> list[str]:
    """For a bob: every step must be the same SIZE, and the loop must close.

    A bob does not travel, so `check_wrap_ratio`'s modular displacement is the
    wrong metric. What must hold is that each hop moves the same distance and
    the frame sequence returns to where it started.
    """
    cs = [centroid(f) for f in frames]
    n = len(cs)
    steps = [
        ((cs[(i + 1) % n][0] - cs[i][0]) ** 2 + (cs[(i + 1) % n][1] - cs[i][1]) ** 2)
        ** 0.5
        for i in range(n)
    ]
    lo, hi = min(steps), max(steps)
    if lo <= 0:
        msg = f"{label}: a step has zero displacement {[round(s, 3) for s in steps]}"
        raise GateError(msg)
    ratio = hi / lo
    if ratio > tol + RATIO_EPS:
        msg = (
            f"{label}: bob step ratio {ratio:.3f} > {tol} "
            f"steps={[round(s, 2) for s in steps]} — uneven hop"
        )
        raise GateError(msg)
    return [
        f"{label}: bob steps equal (ratio {ratio:.3f}) {[round(s, 2) for s in steps]} OK"
    ]


def main() -> None:
    """Gate a GIF: python3 gates.py <gif> [min_margin] [--no-wrap|--bob]."""
    gif = Path(sys.argv[1])
    need = int(sys.argv[2]) if len(sys.argv) > MIN_FRAMES else DEFAULT_MARGIN
    is_bob = "--bob" in sys.argv
    do_wrap = "--no-wrap" not in sys.argv and not is_bob
    frames = frames_rgba(gif)
    out: list[str] = []
    try:
        for i, f in enumerate(frames, 1):
            out += check_margins(f, need, f"{gif.name} f{i}")
        out += check_motion(frames, gif.name)
        # A bob revisits one height by design; travelling motion must not.
        out += check_distinct(frames, gif.name, 3 if is_bob else len(frames))
        if is_bob:
            out += check_oscillation(frames, gif.name, 1.0)
        elif do_wrap:
            out += check_wrap_ratio(frames, gif.name, 1.0)
    except GateError as exc:
        for line in out:
            sys.stdout.write(f"  {line}\n")
        sys.stdout.write(f"FAIL {exc}\n")
        raise SystemExit(1) from exc
    for line in out:
        sys.stdout.write(f"  {line}\n")
    sys.stdout.write(f"PASS {gif.name}\n")


if __name__ == "__main__":
    main()
