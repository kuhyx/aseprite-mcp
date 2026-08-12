# Deterministic checks — how to stop shipping broken pixel art

## The problem this solves

Across one session the portrait attempts failed the SAME way repeatedly:

| Bug | Times | Why eyes didn't catch it |
|---|---|---|
| Fringe erased by the face-cut | 4 | Looked "fine" until exported and studied |
| Mouth silently dropped (cel bounds) | 4 | A 3px feature; invisible at a glance |
| `outline_cel` run twice | 1 | Thickened edges look intentional |
| Concave `draw_polygon` wrote nothing | 2 | Call returned SUCCESS |

Every one of these is **machine-detectable**. None needed judgement. Relying on
"export and look" is what let them through — and it means 8-10 mutations
happened between looks, so errors compounded and the cause was ambiguous.

**Rule: verify after every meaningful step, not at the end.** Cheap checks
after each phase; a `Read` of the exported PNG after each PHASE (face done,
hair done, features done), not after the whole drawing.

## Check 1 — colour census (catches missing features + wrong mass balance)

```
get_color_stats(filename, top=16)
```

Assert:

- **Every palette colour you intended to use APPEARS.** If the mouth tone is
  absent, the mouth is absent. This caught a missing mouth that four visual
  inspections missed.
- **For portraits: hair pixels > skin pixels.** In the reference, hair
  dominates the silhouette and the face is a small bright shape. A portrait
  where skin is the largest colour is the "big pale dome" that kuhy calls a
  **potato**. Measured on a failed attempt: skin 2633 vs hair-base 1887 —
  wrong way round, and detectable in one call.
- **Unique colours 6-12.** More means noise.

## Check 2 — region probe (catches silent write failures)

```
get_composite_rect(filename, x, y, width, height)
```

After drawing ANY feature into a new area, probe it. If the pixels are the
background/skin colour, the write did not land — usually the `draw_pixels_at`
cel-bounds trap or a concave `draw_polygon`. **Never re-draw in a different
colour and hope; probe first.**

## Check 3 — scene validation

```
validate_scene(filename, required_layers=["body","skin","hair","features"])
```

Confirms layers and cels exist before you rely on them.

## Check 4 — silhouette rows (catches shape bugs)

Read the exported PNG with PIL and print per-row extents, or dump a character
map of a region (skin / hair / lash / white). Printing the reference's eye
region as ASCII is what finally revealed that anime eyes are **diagonal
almonds with white as the dominant element** — six visual inspections had not
told me that.

This is also how to lift structure from a reference instead of re-deriving it
from prose: measure the reference, copy the numbers.

## Phase gates

Run these between phases, and STOP on failure rather than continuing:

1. **After the face**: export + Read. Silhouette smooth? No square steps?
2. **After the hair**: export + Read, and `get_color_stats` — hair must
   already exceed skin. Face still open (not a hood)?
3. **After features**: `get_color_stats` — every feature colour present?
4. **Before outlining**: outline exactly once, then never again.
